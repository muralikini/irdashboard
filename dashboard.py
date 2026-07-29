import gzip
import json
import os
import tempfile
import pandas as pd
import plotly.express as px
import streamlit as st
import io          # <-- NEW
import zipfile     # <-- NEW

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="IR & CEC EDID Signal Intelligence",
    page_icon="📊",
    layout="wide",
)

# -----------------------------------------------------------------------------
# 2. Authentication Wrapper
# -----------------------------------------------------------------------------
def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Use st.secrets to securely check the password
        if st.session_state.get("password", "") == st.secrets.get("app_password", ""):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password in session state
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    # Show input for password
    st.title("🔒 Authentication Required")
    st.write("Please enter the password to access the Intelligence Hub.")
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

# Stop execution if password is not correct
if not check_password():
    st.stop()

# -----------------------------------------------------------------------------
# Dependency Linking for IR Signal Parsing
# -----------------------------------------------------------------------------
try:
  from signal_parser import RdPlsPython
  from decoders.decoder_registry import try_all_decoders

  # ---> NEW ENCODER IMPORTS HERE <---
  from encoders.encoder_registry import generate_pulses
  from encoders.packager import create_raw_bytes

  def parse_and_decode_signal(filepath):
    """Extracts mark/space data from a raw file and attempts to decode it."""
    parser = RdPlsPython()
    parser.process_file(filepath)

    if not parser.mark_space_data:
      return {"status": "Error", "message": "No mark/space data extracted."}

    return try_all_decoders(parser.mark_space_data)

except ImportError as e:
  parse_and_decode_signal = None
  print(f"Decoder import warning: {e}")

# -----------------------------------------------------------------------------
# EDID Parser Helper Function (Pure Python)
# -----------------------------------------------------------------------------
def parse_edid_hex(hex_str):
  """Parses raw VESA EDID hex strings into structured display metadata."""
  if not hex_str or not isinstance(hex_str, str):
    return {"status": "Error", "message": "No EDID hex string provided."}

  clean_hex = hex_str.replace(" ", "").strip()
  if len(clean_hex) < 256:
    return {
        "status": "Error",
        "message": (
            f"Invalid EDID length ({len(clean_hex)//2} bytes). Must be at"
            " least 128 bytes (256 hex chars)."
        ),
    }

  try:
    data = bytes.fromhex(clean_hex)
  except ValueError:
    return {"status": "Error", "message": "Failed to decode hex string."}

  header = data[0:8]
  valid_header = header == b"\x00\xff\xff\xff\xff\xff\xff\x00"

  m_int = (data[8] << 8) | data[9]
  c1 = chr(((m_int >> 10) & 0x1F) + 64)
  c2 = chr(((m_int >> 5) & 0x1F) + 64)
  c3 = chr((m_int & 0x1F) + 64)
  mfg_id = f"{c1}{c2}{c3}"

  prod_code = f"0x{(data[11] << 8) | data[10]:04X}"
  serial_num = (data[15] << 24) | (data[14] << 16) | (data[13] << 8) | data[12]

  week = data[16]
  year = data[17] + 1990
  ver = f"{data[18]}.{data[19]}"

  is_digital = bool(data[20] & 0x80)
  width_cm = data[21]
  height_cm = data[22]
  diag_inches = (
      round(((width_cm**2 + height_cm**2) ** 0.5) / 2.54, 1)
      if (width_cm and height_cm)
      else "N/A"
  )

  monitor_name = "N/A"
  ranges = "N/A"
  for offset in (54, 72, 90, 108):
    desc = data[offset : offset + 18]
    if len(desc) == 18 and desc[0:3] == b"\x00\x00\x00":
      tag = desc[3]
      if tag == 0xFC: 
        monitor_name = (
            desc[5:].decode("ascii", errors="ignore").strip("\x0a\x20\x00")
        )
      elif tag == 0xFD: 
        ranges = (
            f"V: {desc[5]}-{desc[6]} Hz | H: {desc[7]}-{desc[8]} kHz | Max"
            f" Pixel Clock: {desc[9]*10} MHz"
        )

  ext_blocks = data[126] if len(data) >= 127 else 0
  checksum = data[127]
  calc_checksum = (256 - (sum(data[:127]) % 256)) % 256
  checksum_valid = checksum == calc_checksum

  return {
      "status": "Success",
      "valid_header": valid_header,
      "mfg_id": mfg_id,
      "product_code": prod_code,
      "serial_number": serial_num if serial_num > 0 else "N/A",
      "manufactured": (
          f"Week {week}, {year}" if week > 0 else f"Year {year}"
      ),
      "edid_version": ver,
      "signal_type": "Digital (HDMI/DVI)" if is_digital else "Analog (VGA)",
      "screen_size": (
          f"{width_cm} x {height_cm} cm (~{diag_inches} inches)"
          if diag_inches != "N/A"
          else "N/A"
      ),
      "monitor_name": monitor_name,
      "range_limits": ranges,
      "extension_blocks": ext_blocks,
      "checksum": (
          f"0x{checksum:02X} (Valid)"
          if checksum_valid
          else f"0x{checksum:02X} (Invalid)"
      ),
  }

def hex_osd_to_ascii(hex_str):
  if not hex_str or not isinstance(hex_str, str):
    return ""
  try:
    hex_bytes = hex_str.strip().split()
    ascii_chars = [chr(int(b, 16)) for b in hex_bytes if b.strip()]
    return "".join(ascii_chars).strip()
  except Exception:
    return hex_str

# -----------------------------------------------------------------------------
# SPD InfoFrame Parser Helper Function
# -----------------------------------------------------------------------------
def parse_spd_infoframe(hex_str):
    """Parses an HDMI Source Product Description (SPD) InfoFrame."""
    if not hex_str or not isinstance(hex_str, str):
        return {"status": "Error", "message": "No raw data provided."}

    clean_hex = hex_str.replace(" ", "").strip()
    try:
        data = bytes.fromhex(clean_hex)
    except ValueError:
        return {"status": "Error", "message": "Invalid hex format."}

    if len(data) < 29:
        return {"status": "Error", "message": "Packet too short for an SPD InfoFrame."}

    if data[0] != 0x83:
        return {"status": "Error", "message": f"Not an SPD InfoFrame (Expected 0x83, got 0x{data[0]:02X})"}

    version = data[1]
    length = data[2]
    checksum = data[3]
    
    calc_checksum = sum(data[:4 + length]) & 0xFF
    checksum_valid = calc_checksum == 0

    vendor_bytes = data[4:12]
    vendor_name = vendor_bytes.decode('ascii', errors='ignore').strip('\x00')

    product_bytes = data[12:28]
    product_desc = product_bytes.decode('ascii', errors='ignore').strip('\x00')

    source_type_byte = data[28]
    source_mapping = {
        0x00: "Unknown", 0x01: "Digital STB", 0x02: "DVD Player",
        0x03: "D-VHS", 0x04: "HDD Videorecorder", 0x05: "DTV",
        0x06: "DVCR", 0x07: "PVR", 0x08: "Game Console",
        0x09: "PC General", 0x0A: "Digital Camera", 0x0B: "Media Receiver"
    }
    source_type_str = source_mapping.get(source_type_byte, f"Reserved/Other (0x{source_type_byte:02X})")

    return {
        "status": "Success",
        "version": version,
        "length": length,
        "checksum_valid": checksum_valid,
        "vendor_name": vendor_name,
        "product_description": product_desc,
        "source_device_type": source_type_str
    }

st.title("📡 Signal Intelligence Hub")
st.caption("IR matching, EDID hardware decoding, and HDMI InfoFrame analytics.")

# -----------------------------------------------------------------------------
# 3. Data Loading Functions
# -----------------------------------------------------------------------------
json_gz_path = "batch_passed.json.gz"
json_path = "batch_passed.json"
cec_json_path = "master_edid_data.json.gz"
infoframe_json_path = "infoframe_data.json"

@st.cache_data
def load_and_parse_json(file_source):
  if isinstance(file_source, str):
    if file_source.endswith(".gz"):
      with gzip.open(file_source, "rt", encoding="utf-8") as f:
        data = json.load(f)
    else:
      with open(file_source, "r", encoding="utf-8") as f:
        data = json.load(f)
  else:
    if hasattr(file_source, "name") and file_source.name.endswith(".gz"):
      with gzip.open(file_source, "rt") as f:
        data = json.load(f)
    else:
      data = json.load(file_source)

  remotes = data.get("remotes", {})
  remote_summary = []
  key_signals = []

  for folder_id, remote_data in remotes.items():
    meta = remote_data.get("metadata", {})
    keys = remote_data.get("keys", {})

    brand = meta.get("brand") or "Unknown"
    device = meta.get("device") or "Unknown"
    subdevice = meta.get("subdevice") or "N/A"
    model = meta.get("model") or "N/A"
    devicemodel = meta.get("devicemodel") or "N/A"
    country = meta.get("country") or "Unknown"
    region = meta.get("region") or "Unknown"

    remote_summary.append({
        "Folder ID": folder_id,
        "Brand": brand,
        "Device": device,
        "Subdevice": subdevice,
        "Model": model,
        "Device Model": devicemodel,
        "Country": country,
        "Region": region,
        "Total Keys": len(keys),
    })

    for key_name, key_info in keys.items():
      decode = key_info.get("decode_data", {})
      if isinstance(decode, list):
        decode = decode[0] if len(decode) > 0 else {}

      protocol = decode.get("protocol", "Unknown")
      address = decode.get("address", "N/A")
      command = decode.get("command", "N/A")
      payload = decode.get("payload", "N/A")

      if str(address) != "N/A" and str(command) != "N/A":
        sig_code = f"{protocol} | Addr: {address} | Cmd: {command}"
      elif str(payload) != "N/A":
        sig_code = f"{protocol} | Payload: {payload}"
      else:
        sig_code = f"{protocol} | Addr: {address} | Cmd: {command}"

      key_signals.append({
          "Folder ID": folder_id,
          "Brand": brand,
          "Device": device,
          "Model": model,
          "Region": region,
          "Country": country,
          "Key Name": key_name,
          "Protocol": protocol,
          "Address": address,
          "Command": command,
          "Payload": payload,
          "Signal Code": sig_code,
          "Source File": key_info.get("source_file", ""),
      })

  return pd.DataFrame(remote_summary), pd.DataFrame(key_signals)

@st.cache_data
def load_cec_json(file_path):
  if os.path.exists(file_path):
    # Check if the file is compressed
    if file_path.endswith('.gz'):
        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            data = json.load(f)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
    df = pd.DataFrame(data)
    if "OSD Name" in df.columns:
        df["OSD ASCII"] = df["OSD Name"].apply(hex_osd_to_ascii)
    return df
  return pd.DataFrame()

@st.cache_data
def load_infoframe_json(file_path):
  if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
      data = json.load(f)
    return pd.DataFrame(data)
  return pd.DataFrame()

# -----------------------------------------------------------------------------
# 4. Cached Heavy Aggregation Helpers
# -----------------------------------------------------------------------------
@st.cache_data
def compute_cross_brand(df_valid):
  cross = (
      df_valid.groupby("Signal Code")
      .agg(
          Unique_Brands=("Brand", "nunique"),
          Brand_Names=("Brand", lambda x: ", ".join(sorted(set(x)))),
          Remotes_Count=("Folder ID", "nunique"),
          Folders=("Folder ID", lambda x: ", ".join(sorted(set(x)))),
          Keys_Mapped=("Key Name", lambda x: ", ".join(sorted(set(x)))),
          Total_Signals=("Key Name", "count"),
      )
      .reset_index()
  )
  return cross[cross["Unique_Brands"] > 1].sort_values(
      by="Unique_Brands", ascending=False
  )

@st.cache_data
def compute_intra_remote(df_valid):
  intra = (
      df_valid.groupby(["Folder ID", "Brand", "Signal Code"])
      .agg(
          Duplicate_Key_Count=("Key Name", "count"),
          Buttons_Sharing_Code=("Key Name", lambda x: ", ".join(x)),
      )
      .reset_index()
  )
  return intra[intra["Duplicate_Key_Count"] > 1].sort_values(
      by="Duplicate_Key_Count", ascending=False
  )

@st.cache_data
def compute_dictionary(df_valid):
  dict_df = (
      df_valid.groupby(["Protocol", "Address", "Command", "Payload"])
      .agg(
          Total_Occurrences=("Key Name", "count"),
          Brands=("Brand", lambda x: ", ".join(sorted(set(x)))),
          Devices=("Device", lambda x: ", ".join(sorted(set(x)))),
          Models=(
              "Model",
              lambda x: ", ".join(
                  sorted(set([str(m) for m in x if str(m) != "N/A"]))
              ),
          ),
          Folders=("Folder ID", lambda x: ", ".join(sorted(set(x)))),
          Mapped_Keys=("Key Name", lambda x: ", ".join(sorted(set(x)))),
      )
      .reset_index()
  )
  return dict_df.sort_values(by="Total_Occurrences", ascending=False)

# -----------------------------------------------------------------------------
# 5. Sidebar Data Ingestion
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Data Options & Filters")
uploaded_file = st.sidebar.file_uploader(
    "Upload custom IR JSON/GZ", type=["json", "gz"]
)

if uploaded_file is not None:
  df_remotes, df_keys = load_and_parse_json(uploaded_file)
elif os.path.exists(json_gz_path):
  df_remotes, df_keys = load_and_parse_json(json_gz_path)
elif os.path.exists(json_path):
  df_remotes, df_keys = load_and_parse_json(json_path)
else:
  df_remotes, df_keys = pd.DataFrame(), pd.DataFrame()

df_cec = load_cec_json(cec_json_path)
df_infoframe = load_infoframe_json(infoframe_json_path)

st.sidebar.subheader("Filter Analytics Dashboard")
if not df_remotes.empty:
  selected_region = st.sidebar.multiselect(
      "Region", options=sorted(df_remotes["Region"].unique())
  )
  selected_brand = st.sidebar.multiselect(
      "Brand", options=sorted(df_remotes["Brand"].unique())
  )
  selected_device = st.sidebar.multiselect(
      "Device", options=sorted(df_remotes["Device"].unique())
  )

  filtered_remotes = df_remotes.copy()
  filtered_keys = df_keys.copy()

  if selected_region:
    filtered_remotes = filtered_remotes[
        filtered_remotes["Region"].isin(selected_region)
    ]
    filtered_keys = filtered_keys[
        filtered_keys["Region"].isin(selected_region)
    ]

  if selected_brand:
    filtered_remotes = filtered_remotes[
        filtered_remotes["Brand"].isin(selected_brand)
    ]
    filtered_keys = filtered_keys[filtered_keys["Brand"].isin(selected_brand)]

  if selected_device:
    filtered_remotes = filtered_remotes[
        filtered_remotes["Device"].isin(selected_device)
    ]
    filtered_keys = filtered_keys[
        filtered_keys["Device"].isin(selected_device)
    ]

# -----------------------------------------------------------------------------
# 6. Main Navigation Tabs
# -----------------------------------------------------------------------------
tab_analytics, tab_matcher, tab_finder, tab_explorer, tab_cec, tab_info, tab_gen = st.tabs([
    "📊 Database Analytics",
    "🔍 Direct Signal Matcher",
    "📂 Smart Folder Finder",
    "📱 Device & Brand Explorer",
    "📺 CEC & EDID Intelligence",
    "🗃️ SPD InfoFrame Decoder",
    "🛠️ IR Signal Generator"
])

# =============================================================================
# TAB 1: DATABASE ANALYTICS
# =============================================================================
with tab_analytics:
  if df_remotes.empty:
    st.info("Please load an IR database JSON file to view Analytics.")
  else:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Folders / Remotes", len(filtered_remotes))
    m2.metric("Total Keys / Signals", len(filtered_keys))
    m3.metric("Unique Brands", filtered_remotes["Brand"].nunique())
    m4.metric("Unique Device Types", filtered_remotes["Device"].nunique())
    m5.metric(
        "Avg Keys / Remote",
        f"{filtered_remotes['Total Keys'].mean():.1f}"
        if len(filtered_remotes) > 0
        else "0",
    )
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
      st.subheader("🏷️ Brand Statistics")
      brand_counts = filtered_remotes["Brand"].value_counts().reset_index()
      brand_counts.columns = ["Brand", "Count"]
      st.plotly_chart(
          px.bar(
              brand_counts, x="Brand", y="Count", text="Count", color="Brand", title="Remotes per Brand",
          ), use_container_width=True,
      )

    with col2:
      st.subheader("📺 Device Statistics")
      device_counts = filtered_remotes["Device"].value_counts().reset_index()
      device_counts.columns = ["Device", "Count"]
      st.plotly_chart(
          px.pie(
              device_counts, names="Device", values="Count", hole=0.4, title="Device Type Distribution",
          ), use_container_width=True,
      )

    st.divider()

    col3, col4 = st.columns(2)
    with col3:
      st.subheader("📡 Protocol Statistics")
      proto_counts = filtered_keys["Protocol"].value_counts().reset_index()
      proto_counts.columns = ["Protocol", "Total Keys"]
      st.plotly_chart(
          px.bar(
              proto_counts, x="Total Keys", y="Protocol", orientation="h", text="Total Keys", color="Protocol", title="Signals by IR Protocol",
          ), use_container_width=True,
      )

    with col4:
      st.subheader("🌍 Region & Country Coverage")
      region_counts = (
          filtered_remotes.groupby(["Region", "Country"])
          .size()
          .reset_index(name="Count")
      )
      st.plotly_chart(
          px.sunburst(
              region_counts, path=["Region", "Country"], values="Count", title="Geographic Breakdown",
          ), use_container_width=True,
      )

    st.divider()

    st.subheader("🔌 Protocol-to-Brand Mapping Analytics")
    pb_col1, pb_col2 = st.columns(2)
    proto_brand_df = (
        filtered_keys.groupby(["Protocol", "Brand"])
        .size()
        .reset_index(name="Signal Count")
    )
    with pb_col1:
      st.plotly_chart(
          px.bar(
              proto_brand_df, x="Protocol", y="Signal Count", color="Brand", title="Protocol Stacked by Brand", barmode="stack", text="Signal Count",
          ), use_container_width=True,
      )
    with pb_col2:
      st.plotly_chart(
          px.sunburst(
              proto_brand_df, path=["Brand", "Protocol"], values="Signal Count", title="Brand -> Protocol Breakdown",
          ), use_container_width=True,
      )

    st.markdown("#### 📋 Protocol vs. Brand Matrix")
    st.dataframe(
        pd.crosstab(
            filtered_keys["Protocol"], filtered_keys["Brand"], margins=True, margins_name="Total Signals",
        ), use_container_width=True,
    )
    st.divider()

    st.subheader("🔍 Signal Duplication & Brand Overlap Analysis")
    valid_keys = filtered_keys[filtered_keys["Protocol"] != "Unknown"]

    dup_tab1, dup_tab2 = st.tabs(
        ["⚡ Cross-Brand Code Sharing", "🔁 Same-Remote Duplicate Commands"]
    )
    with dup_tab1:
      st.markdown("##### Signals Shared Across Multiple Brands")
      shared_signals = compute_cross_brand(valid_keys)
      if len(shared_signals) > 0:
        st.success(f"Found {len(shared_signals)} unique Hex signal signatures shared across different brands.")
        st.dataframe(shared_signals, use_container_width=True, hide_index=True)
      else:
        st.info("No cross-brand hex overlaps detected.")

    with dup_tab2:
      st.markdown("##### Duplicate Hex Commands Within the Same Remote Folder")
      same_remote_dups = compute_intra_remote(valid_keys)
      if len(same_remote_dups) > 0:
        st.warning("Found instances where a single remote uses identical Hex codes for multiple buttons.")
        st.dataframe(same_remote_dups, use_container_width=True, hide_index=True)
      else:
        st.info("No intra-remote key collisions detected.")

    st.divider()

    st.subheader("🗂️ Universal Hex Dictionary (Reverse Lookup)")
    st.markdown("Grouped strictly by Protocol, Address, and Command.")
    st.dataframe(
        compute_dictionary(valid_keys), use_container_width=True, hide_index=True,
    )
    st.divider()

    st.subheader("🔄 Device-Brand Coverage Matrix")
    st.dataframe(
        pd.crosstab(
            filtered_remotes["Brand"], filtered_remotes["Device"], margins=True, margins_name="Total",
        ), use_container_width=True,
    )
    st.divider()

    st.subheader("📁 Processed Folders Explorer")
    e_tab1, e_tab2 = st.tabs(
        ["Remote Folders Summary", "Detailed Signals & Decodes"]
    )
    with e_tab1:
      st.dataframe(filtered_remotes, use_container_width=True, hide_index=True)
    with e_tab2:
      search_key = st.text_input("Filter signals by Key Name:")
      display_keys = filtered_keys
      if search_key:
        display_keys = display_keys[
            display_keys["Key Name"].str.contains(search_key, case=False, na=False)
        ]
      st.dataframe(display_keys, use_container_width=True, hide_index=True)

# =============================================================================
# TAB 2: DIRECT SIGNAL MATCHER
# =============================================================================
with tab_matcher:
  st.header("🎯 Direct Raw Signal Matcher")
  st.write(
      "Upload a raw signal file (`.SIG`, `.U1`, or `.U2`) or manually enter"
      " decodes to query the complete database across all folders."
  )

  input_method = st.radio(
      "Select Input Mode:", ["Upload Signal File (.SIG / .U1 / .U2)", "Manual Hex Search"], horizontal=True,
  )
  search_protocol, search_address, search_command = None, None, None

  if input_method == "Upload Signal File (.SIG / .U1 / .U2)":
    uploaded_signal = st.file_uploader(
        "Upload a raw `.SIG`, `.U1`, or `.U2` file", type=["sig", "u1", "u2"], key="matcher_file_uploader",
    )
    if uploaded_signal:
      ext = uploaded_signal.name.split(".")[-1].lower()
      with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(uploaded_signal.getvalue())
        tmp_path = tmp.name
      try:
        decoded = (
            parse_and_decode_signal(tmp_path) if parse_and_decode_signal else None
        )
        if (
            decoded and isinstance(decoded, dict) and decoded.get("status") in ["Success", "Repeat"]
        ):
          search_protocol = decoded.get("protocol")
          search_address = decoded.get("address")
          search_command = decoded.get("command")
          st.success(
              f"**Successfully Decoded File:** Protocol: `{search_protocol}`,"
              f" Address: `{search_address}`, Command: `{search_command}`"
          )
        else:
          st.warning("⚠️ Decoder failed to identify this signal format. Please enter hex values manually:")
          c_p, c_a, c_c = st.columns(3)
          search_protocol = c_p.text_input("Protocol", value="", placeholder="e.g. NEC", key="up_proto")
          search_address = c_a.text_input("Address", value="", placeholder="e.g. 0x4", key="up_addr")
          search_command = c_c.text_input("Command", value="", placeholder="e.g. 0xf0", key="up_cmd")
      except Exception as e:
        st.error(f"Error decoding signal file: {e}")
      finally:
        if os.path.exists(tmp_path):
          os.remove(tmp_path)
  else:
    c_p, c_a, c_c = st.columns(3)
    search_protocol = c_p.text_input("Protocol (e.g. NEC, RC5, SONY)", value="", placeholder="e.g. NEC", key="man_proto")
    search_address = c_a.text_input("Address Hex (e.g. 0x4)", value="", placeholder="e.g. 0x4", key="man_addr")
    search_command = c_c.text_input("Command Hex (e.g. 0xf0)", value="", placeholder="e.g. 0xf0", key="man_cmd")

  if search_protocol or search_address or search_command:
    st.divider()
    st.subheader("🔎 Search Parameters")
    st.write(
        f"**Protocol:** `{search_protocol or 'Any'}` | **Address:**"
        f" `{search_address or 'Any'}` | **Command:**"
        f" `{search_command or 'Any'}`"
    )

    matches = df_keys.copy()
    if search_protocol:
      matches = matches[matches["Protocol"].astype(str).str.upper() == str(search_protocol).strip().upper()]
    if search_address:
      matches = matches[matches["Address"].astype(str).str.strip().str.lower() == str(search_address).strip().lower()]
    if search_command:
      matches = matches[matches["Command"].astype(str).str.strip().str.lower() == str(search_command).strip().lower()]

    st.subheader(f"📋 Exact Database Matches ({len(matches)} found)")
    if len(matches) > 0:
      output_cols = [
          "Folder ID", "Brand", "Device", "Model", "Key Name", "Protocol", "Address", "Command", "Country", "Region", "Source File",
      ]
      st.dataframe(matches[output_cols].reset_index(drop=True), use_container_width=True)
    else:
      st.warning("No records matched the specified protocol and hex criteria.")

# =============================================================================
# TAB 3: SMART FOLDER FINDER
# =============================================================================
with tab_finder:
  st.header("📂 Smart Folder Finder")
  st.write(
      "Find remote folders that contain a specific combination of keys for a"
      " target device. Adjust the tolerance slider if you don't need a 100%"
      " perfect match."
  )

  if not df_remotes.empty:
    col1, col2, col3 = st.columns(3)
    with col1:
      all_devices = sorted(df_remotes["Device"].unique())
      req_devices = st.multiselect("Target Device(s) [Mandatory]", options=all_devices)
    with col2:
      all_regions = sorted(df_remotes["Region"].unique())
      req_regions = st.multiselect("Target Region(s) [Optional]", options=all_regions)
    with col3:
      all_keys = sorted(df_keys["Key Name"].dropna().unique())
      req_keys = st.multiselect("Required Keys [Mandatory]", options=all_keys)

    if len(req_keys) > 0:
      max_tol = len(req_keys)
      min_tol = 1 if max_tol == 1 else 2
      tolerance = st.slider(
          "Minimum Keys Match Tolerance", min_value=min_tol, max_value=max_tol, value=max_tol,
          help="Set the minimum number of requested keys a folder must have to be considered a match.",
      )
    else:
      tolerance = 0
      st.info("Select keys above to set the match tolerance.")

    if st.button("Search Folders", type="primary", use_container_width=True):
      if not req_devices:
        st.error("⚠️ Please select at least one Target Device.")
      elif not req_keys:
        st.error("⚠️ Please select at least one Required Key.")
      else:
        with st.spinner("Scanning database for matching folders..."):
          cand_remotes = df_remotes[df_remotes["Device"].isin(req_devices)]
          if req_regions:
            cand_remotes = cand_remotes[cand_remotes["Region"].isin(req_regions)]

          valid_folders = cand_remotes["Folder ID"].unique()
          cand_keys = df_keys[
              (df_keys["Folder ID"].isin(valid_folders)) & (df_keys["Key Name"].isin(req_keys))
          ]

          if cand_keys.empty:
            st.warning("No folders found matching the specified device and key criteria.")
          else:
            match_counts = cand_keys.groupby("Folder ID")["Key Name"].nunique().reset_index()
            match_counts.rename(columns={"Key Name": "Matched Keys Count"}, inplace=True)
            passed_folders = match_counts[match_counts["Matched Keys Count"] >= tolerance]

            if passed_folders.empty:
              st.warning(f"No folders met the minimum tolerance of {tolerance} matching keys.")
            else:
              results = pd.merge(passed_folders, cand_remotes, on="Folder ID", how="left")

              def get_matched_keys(fid):
                return ", ".join(sorted(cand_keys[cand_keys["Folder ID"] == fid]["Key Name"].unique()))

              results["Matched Keys"] = results["Folder ID"].apply(get_matched_keys)

              def get_missing_keys(matched_str):
                matched_list = ([k.strip() for k in matched_str.split(",")] if matched_str else [])
                missing = set(req_keys) - set(matched_list)
                return (", ".join(sorted(missing)) if missing else "None (100% Match)")

              results["Missing Keys"] = results["Matched Keys"].apply(get_missing_keys)
              results = results.sort_values(by=["Matched Keys Count", "Brand"], ascending=[False, True])
              st.success(f"🎉 Found {len(results)} folders matching your criteria!")

              display_cols = [
                  "Folder ID", "Brand", "Device", "Model", "Region", "Matched Keys Count", "Matched Keys", "Missing Keys",
              ]
              st.dataframe(results[display_cols], use_container_width=True, hide_index=True)

# =============================================================================
# TAB 4: DEVICE & BRAND EXPLORER
# =============================================================================
with tab_explorer:
  st.header("📱 Device & Brand Explorer")
  st.write(
      "Search for remote folders by Device, Brand, and Model. Returns all"
      " matching folders along with a complete list of all supported keys."
  )

  if not df_remotes.empty:
    col1, col2, col3 = st.columns(3)
    with col1:
      all_devices_t4 = sorted(df_remotes["Device"].unique())
      search_devices = st.multiselect("Target Device(s) [Mandatory]", options=all_devices_t4, key="t4_dev")
    with col2:
      all_brands_t4 = sorted(df_remotes["Brand"].unique())
      search_brands = st.multiselect("Target Brand(s) [Mandatory]", options=all_brands_t4, key="t4_brand")
    with col3:
      search_model = st.text_input("Model Name (Min 3 chars) [Optional]", value="", key="t4_model", placeholder="e.g. AKB")

    if st.button("Search Database", type="primary", use_container_width=True, key="t4_btn"):
      if not search_devices:
        st.error("⚠️ Please select at least one Target Device.")
      elif not search_brands:
        st.error("⚠️ Please select at least one Target Brand.")
      else:
        with st.spinner("Searching for matching folders..."):
          cand = df_remotes[
              (df_remotes["Device"].isin(search_devices)) & (df_remotes["Brand"].isin(search_brands))
          ].copy()

          model_query = search_model.strip()
          if len(model_query) > 0:
            if len(model_query) < 3:
              st.warning("⚠️ Model input ignored. Please enter at least 3 characters to apply the model filter.")
            else:
              cand = cand[cand["Model"].astype(str).str.contains(model_query, case=False, na=False)]

          if cand.empty:
            st.warning("No folders found matching the specified Device, Brand, and Model criteria.")
          else:
            valid_fids = cand["Folder ID"].unique()
            matched_keys = df_keys[df_keys["Folder ID"].isin(valid_fids)]

            keys_per_folder = (
                matched_keys.groupby("Folder ID")["Key Name"]
                .apply(lambda x: ", ".join(sorted(set(x))))
                .reset_index()
            )
            keys_per_folder.rename(columns={"Key Name": "Supported Keys"}, inplace=True)

            results = pd.merge(cand, keys_per_folder, on="Folder ID", how="left")
            results = results.sort_values(by=["Brand", "Device", "Model"])

            st.success(f"🎉 Found {len(results)} folders matching your criteria!")

            display_cols = [
                "Folder ID", "Brand", "Device", "Model", "Region", "Total Keys", "Supported Keys",
            ]
            st.dataframe(results[display_cols], use_container_width=True, hide_index=True)

# =============================================================================
# TAB 5: CEC & EDID INTELLIGENCE
# =============================================================================
with tab_cec:
  st.header("📺 CEC & EDID Intelligence Hub")
  st.write(
      "Explore Consumer Electronics Control (CEC) status, Vendor IDs, OSD Name"
      " decodes, and parse VESA EDID hardware descriptors."
  )

  if df_cec.empty:
    st.warning("⚠️ `cec_edid_data.json` not found or empty! Please ensure the file is placed in the root directory.")
  else:
    cec_m1, cec_m2, cec_m3, cec_m4 = st.columns(4)
    cec_m1.metric("Total Devices In Dataset", len(df_cec))
    cec_m2.metric("CEC Supported Devices", len(df_cec[df_cec["IS CEC Present"].astype(str).str.upper() == "Y"]))
    cec_m3.metric("CEC Enabled Devices", len(df_cec[df_cec["Is CEC Enabled"].astype(str).str.upper() == "Y"]))
    cec_m4.metric("Unique Brands", df_cec["Brand"].nunique())

    st.divider()

    st.subheader("🔍 Filter CEC Data & Toggle OSD Decoding")

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
      cec_brands = st.multiselect("Filter Brand", options=sorted(df_cec["Brand"].dropna().unique()), key="cec_brand_f")
    with col_f2:
      cec_regions = st.multiselect("Filter Region", options=sorted(df_cec["Region"].dropna().unique()), key="cec_reg_f")
    with col_f3:
      cec_present_filter = st.selectbox("CEC Present?", ["All", "Yes Only (Y)", "No Only (N)"])
    with col_f4:
      osd_display_mode = st.radio(
          "OSD Name View Format:", ["ASCII String", "Hex Bytes", "Both (Hex -> ASCII)"], horizontal=True,
      )

    cec_display_df = df_cec.copy()

    if cec_brands:
      cec_display_df = cec_display_df[cec_display_df["Brand"].isin(cec_brands)]
    if cec_regions:
      cec_display_df = cec_display_df[cec_display_df["Region"].isin(cec_regions)]

    if cec_present_filter == "Yes Only (Y)":
      cec_display_df = cec_display_df[cec_display_df["IS CEC Present"].astype(str).str.upper() == "Y"]
    elif cec_present_filter == "No Only (N)":
      cec_display_df = cec_display_df[cec_display_df["IS CEC Present"].astype(str).str.upper() == "N"]

    if osd_display_mode == "ASCII String":
      cec_display_df["OSD Field Display"] = cec_display_df["OSD ASCII"]
    elif osd_display_mode == "Hex Bytes":
      cec_display_df["OSD Field Display"] = cec_display_df["OSD Name"]
    else:
      def combine_osd(row):
        h = str(row["OSD Name"]).strip()
        a = str(row["OSD ASCII"]).strip()
        return f"{h} ➔ ({a})" if (h and a) else h or a
      cec_display_df["OSD Field Display"] = cec_display_df.apply(combine_osd, axis=1)

    show_edid = st.checkbox("👁️ Show Raw EDID Hex Data in Table", value=False)
    
    table_cols = [
        "Brand", "Model", "Device Type", "Subdevice", "IS CEC Present",
        "Is CEC Enabled", "Vendor ID", "OSD Field Display", "Region", "Country",
    ]
    if show_edid:
        table_cols.append("EDID")

    st.dataframe(cec_display_df[table_cols].reset_index(drop=True), use_container_width=True)

    st.divider()

    st.subheader("🔬 VESA EDID Hardware Decoder")
    st.write("Select a device model from the database or paste a raw EDID hex block below to parse hardware capabilities.")

    decode_source = st.radio("Select EDID Source:", ["Select Model from Dataset", "Paste Custom Hex String"], horizontal=True)

    edid_to_parse = ""

    if decode_source == "Select Model from Dataset":
      has_edid = df_cec[df_cec["EDID"].astype(str).str.strip() != ""]

      if not has_edid.empty:
        has_edid["Select Label"] = (
            has_edid["Brand"].astype(str) + " - " + has_edid["Model"].astype(str) + " (" + has_edid["Country"].astype(str) + ")"
        )

        selected_model_label = st.selectbox("Choose a TV / Display Model:", options=has_edid["Select Label"].unique())
        selected_row = has_edid[has_edid["Select Label"] == selected_model_label].iloc[0]

        edid_to_parse = selected_row["EDID"]

        st.info(
            f"**Selected Model:** {selected_row['Brand']} {selected_row['Model']} | "
            f"**CEC Status:** {selected_row['IS CEC Present']} (Enabled: {selected_row['Is CEC Enabled']}) | "
            f"**Vendor ID:** {selected_row['Vendor ID'] or 'N/A'}"
        )
      else:
        st.warning("No EDID data available in the current dataset.")
    else:
      edid_to_parse = st.text_area("Paste Raw EDID Hex Block (128 or 256 bytes):", height=120, placeholder="00 FF FF FF FF FF FF 00 1E 6D ...")

    if st.button("Decode EDID Data", type="primary", use_container_width=True):
      if not edid_to_parse or len(edid_to_parse.strip()) == 0:
        st.error("⚠️ Please select a model or enter valid EDID hex data.")
      else:
        parsed_res = parse_edid_hex(edid_to_parse)

        if parsed_res.get("status") == "Error":
          st.error(f"⚠️ Decoding Error: {parsed_res.get('message')}")
        else:
          st.success("🎉 EDID Data Successfully Decoded!")

          ed_col1, ed_col2, ed_col3, ed_col4 = st.columns(4)
          ed_col1.metric("Manufacturer PNP ID", parsed_res.get("mfg_id"))
          ed_col2.metric("Parsed Monitor Name", parsed_res.get("monitor_name"))
          ed_col3.metric("Signal Type", parsed_res.get("signal_type"))
          ed_col4.metric("Checksum Result", parsed_res.get("checksum"))

          p_data = {
              "Property": [
                  "PNP Manufacturer Code", "Product Code", "Serial Number", "Manufactured Date",
                  "EDID Structure Version", "Physical Screen Dimensions", "Timing / Refresh Rate Limits",
                  "CEA-861 HDMI Extension Blocks", "Header Validation",
              ],
              "Decoded Value": [
                  parsed_res.get("mfg_id"), parsed_res.get("product_code"), str(parsed_res.get("serial_number")),
                  parsed_res.get("manufactured"), parsed_res.get("edid_version"), parsed_res.get("screen_size"),
                  parsed_res.get("range_limits"), f"{parsed_res.get('extension_blocks')} block(s)",
                  "Valid Standard" if parsed_res.get("valid_header") else "Non-standard Header",
              ],
          }
          st.dataframe(pd.DataFrame(p_data), use_container_width=True)

          with st.expander("🔍 View Raw Hex Stream"):
            st.code(edid_to_parse, language="text")

# =============================================================================
# TAB 6: SPD INFOFRAME DECODER
# =============================================================================
with tab_info:
  st.header("🗃️ SPD InfoFrame Intelligence Hub")
  st.write("Browse and decode HDMI Source Product Description (SPD) InfoFrame data streams to identify connected media hardware.")

  if df_infoframe.empty:
      st.warning("⚠️ `infoframe_data.json` not found or empty! Please place the file in the root directory.")
  else:
      st.dataframe(df_infoframe, use_container_width=True)
      st.divider()

      st.subheader("🔬 SPD InfoFrame Hex Decoder")
      st.write("Select a hardware entry from the database to instantly parse its HDMI InfoFrame packet.")

      valid_info = df_infoframe[df_infoframe["rawdata"].astype(str).str.strip() != ""]

      if valid_info.empty:
          st.warning("No raw hex data available in the InfoFrame dataset.")
      else:
          valid_info["Info Label"] = valid_info["Manufacturer"].astype(str) + " - " + valid_info["sifdescription"].astype(str)
          
          selected_info_label = st.selectbox("Select a Device to Decode:", options=valid_info["Info Label"].unique())
          
          if st.button("Decode InfoFrame Packet", type="primary"):
              selected_info_row = valid_info[valid_info["Info Label"] == selected_info_label].iloc[0]
              raw_hex = selected_info_row["rawdata"]
              
              parsed_spd = parse_spd_infoframe(raw_hex)
              
              if parsed_spd.get("status") == "Error":
                  st.error(f"⚠️ Decoding Error: {parsed_spd.get('message')}")
              else:
                  st.success("🎉 InfoFrame Packet Successfully Decoded!")
                  
                  col_a, col_b, col_c = st.columns(3)
                  col_a.metric("Vendor Name", parsed_spd.get("vendor_name"))
                  col_b.metric("Product Description", parsed_spd.get("product_description"))
                  col_c.metric("Device Profile", parsed_spd.get("source_device_type"))
                  
                  st.markdown("#### 📡 Protocol Headers & Verification")
                  st.write(f"- **InfoFrame Type:** `0x83` (Source Product Description)")
                  st.write(f"- **Version:** `0x{parsed_spd.get('version'):02X}`")
                  st.write(f"- **Length:** `{parsed_spd.get('length')} bytes`")
                  
                  chk_msg = "Valid ✅" if parsed_spd.get("checksum_valid") else "Invalid ❌"
                  st.write(f"- **Checksum:** {chk_msg}")
                  
                  with st.expander("🔍 View Raw Hex Stream"):
                      st.code(raw_hex, language="text")
                    
# =============================================================================
# TAB 7: IR SIGNAL GENERATOR
# =============================================================================
with tab_gen:
    st.header("🛠️ IR Signal Generator")
    st.write("Generate raw signal files based on Protocol, Address, Command, and Payload. Add multiple rows to download a combined ZIP archive.")

    # 1. File Format Selector
    file_format = st.radio("Select Target Format:", [".SIG", ".U1", ".U2"], horizontal=True)

    # 2. Setup Default Dataframe for the Data Editor
    if "gen_keys_df" not in st.session_state:
        st.session_state.gen_keys_df = pd.DataFrame(
            [{"Key Name": "Power", "Protocol": "NEC", "Address (Hex)": "0x04", "Command (Hex)": "0x08", "Payload (Hex)": ""}]
        )

    st.markdown("### ⌨️ Signal Definitions")
    st.caption("Edit the table below. You can paste data directly from Excel or click the '+' at the bottom to add new rows.")
    
    # 3. Dynamic Data Editor
    edited_df = st.data_editor(
        st.session_state.gen_keys_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Key Name": st.column_config.TextColumn("Key Name", required=True),
            "Protocol": st.column_config.SelectboxColumn("Protocol", options=["NEC", "RC5", "RC6", "SONY", "SAMSUNG", "LG", "PANASONIC", "JVC", "SHARP", "RCA", "APPLE", "DENON", "ONKYO"], required=True),
            "Address (Hex)": st.column_config.TextColumn("Address (Hex)"),
            "Command (Hex)": st.column_config.TextColumn("Command (Hex)"),
            "Payload (Hex)": st.column_config.TextColumn("Payload (Hex)")
        }
    )

    st.divider()

    # 4. Actual Encoder Function
    def generate_raw_signal_bytes(protocol, address, command, payload, format_ext):
        """Routes the generation request to the registry and packages the bytes."""
        # 1. Get the Mark/Space pulse array from the registry
        pulses = generate_pulses(protocol, address, command, payload)

        # 2. Package into raw binary bytes at 1 MHz
        raw_binary = create_raw_bytes(pulses, sample_freq_hz=1000000, file_format=format_ext)

        return raw_binary
    

    # 5. Generation & Download Logic
    if st.button("⚙️ Compile & Generate Files", type="primary", use_container_width=True):
        
        # Clean up empty rows
        valid_rows = edited_df.dropna(subset=["Key Name", "Protocol"]).copy()
        valid_rows = valid_rows[valid_rows["Key Name"].str.strip() != ""]

        if valid_rows.empty:
            st.error("⚠️ Please define at least one valid key with a name and protocol.")
        else:
            num_keys = len(valid_rows)
            
            # --- SCENARIO A: SINGLE KEY (Download single file) ---
            if num_keys == 1:
                row = valid_rows.iloc[0]
                filename = f"{row['Key Name'].strip()}{file_format.lower()}"
                
                try:
                    file_bytes = generate_raw_signal_bytes(
                        row['Protocol'], row['Address (Hex)'], row['Command (Hex)'], row['Payload (Hex)'], file_format
                    )
                    st.success(f"Successfully compiled {filename}!")
                    st.download_button(
                        label=f"⬇️ Download {filename}",
                        data=file_bytes,
                        file_name=filename,
                        mime="application/octet-stream"
                    )
                except Exception as e:
                    st.error(f"⚠️ Compilation Error for '{row['Key Name']}': {str(e)}")

            # --- SCENARIO B: MULTIPLE KEYS (Download ZIP file) ---
            else:
                zip_buffer = io.BytesIO()
                
                # Open an in-memory zip file
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for index, row in valid_rows.iterrows():
                        key_name = str(row['Key Name']).strip().replace("/", "_").replace("\\", "_")
                        filename = f"{key_name}{file_format.lower()}"
                        
                        # Generate Bytes
                        file_bytes = generate_raw_signal_bytes(
                            row['Protocol'], row['Address (Hex)'], row['Command (Hex)'], row['Payload (Hex)'], file_format
                        )
                        
                        # Write bytes to the specific filename inside the zip
                        zip_file.writestr(filename, file_bytes)

                st.success(f"Successfully compiled {num_keys} keys into a ZIP archive!")
                st.download_button(
                    label="⬇️ Download All Keys (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"Generated_Signals{file_format.lower()}.zip",
                    mime="application/zip"
                )