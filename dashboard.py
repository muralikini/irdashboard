import gzip
import json
import os
import tempfile
import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# Dependency Linking for Signal Parsing
# -----------------------------------------------------------------------------
try:
    from signal_parser import RdPlsPython
    from decoders.decoder_registry import try_all_decoders

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
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="IR Remote Signal Analytics & Identification",
    page_icon="📊",
    layout="wide",
)

st.title("📡 IR Remote Signal Intelligence & Analytics")
st.caption(
    "Comprehensive coverage metrics, protocol analytics, and instant exact"
    " signal matching."
)

# -----------------------------------------------------------------------------
# 2. Data Loading & Parsing Function (Optimized)
# -----------------------------------------------------------------------------
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

      # Generate Signal Code here for instant performance later
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

# -----------------------------------------------------------------------------
# 3. Cached Heavy Aggregation Helpers (Prevents UI Freezing)
# -----------------------------------------------------------------------------
@st.cache_data
def compute_cross_brand(df_valid):
    cross = df_valid.groupby("Signal Code").agg(
        Unique_Brands=("Brand", "nunique"),
        Brand_Names=("Brand", lambda x: ", ".join(sorted(set(x)))),
        Remotes_Count=("Folder ID", "nunique"),
        Folders=("Folder ID", lambda x: ", ".join(sorted(set(x)))),
        Keys_Mapped=("Key Name", lambda x: ", ".join(sorted(set(x)))),
        Total_Signals=("Key Name", "count"),
    ).reset_index()
    return cross[cross["Unique_Brands"] > 1].sort_values(by="Unique_Brands", ascending=False)

@st.cache_data
def compute_intra_remote(df_valid):
    intra = df_valid.groupby(["Folder ID", "Brand", "Signal Code"]).agg(
        Duplicate_Key_Count=("Key Name", "count"),
        Buttons_Sharing_Code=("Key Name", lambda x: ", ".join(x)),
    ).reset_index()
    return intra[intra["Duplicate_Key_Count"] > 1].sort_values(by="Duplicate_Key_Count", ascending=False)

@st.cache_data
def compute_dictionary(df_valid):
    dict_df = df_valid.groupby(["Protocol", "Address", "Command", "Payload"]).agg(
        Total_Occurrences=("Key Name", "count"),
        Brands=("Brand", lambda x: ", ".join(sorted(set(x)))),
        Devices=("Device", lambda x: ", ".join(sorted(set(x)))),
        Models=("Model", lambda x: ", ".join(sorted(set([str(m) for m in x if str(m) != "N/A"])))),
        Folders=("Folder ID", lambda x: ", ".join(sorted(set(x)))),
        Mapped_Keys=("Key Name", lambda x: ", ".join(sorted(set(x)))),
    ).reset_index()
    return dict_df.sort_values(by="Total_Occurrences", ascending=False)

# -----------------------------------------------------------------------------
# 4. Sidebar Data Selection & Filtering
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Data Options & Filters")

json_gz_path = "batch_passed.json.gz"
json_path = "batch_passed.json"
uploaded_file = st.sidebar.file_uploader("Upload custom JSON or GZ", type=["json", "gz"])

if uploaded_file is not None:
  df_remotes, df_keys = load_and_parse_json(uploaded_file)
elif os.path.exists(json_gz_path):
  df_remotes, df_keys = load_and_parse_json(json_gz_path)
elif os.path.exists(json_path):
  df_remotes, df_keys = load_and_parse_json(json_path)
else:
  st.error("No dataset found! Ensure batch_passed.json or batch_passed.json.gz is present.")
  st.stop()

st.sidebar.subheader("Filter Analytics Dashboard")
selected_region = st.sidebar.multiselect("Region", options=sorted(df_remotes["Region"].unique()))
selected_brand = st.sidebar.multiselect("Brand", options=sorted(df_remotes["Brand"].unique()))
selected_device = st.sidebar.multiselect("Device", options=sorted(df_remotes["Device"].unique()))

filtered_remotes = df_remotes.copy()
filtered_keys = df_keys.copy()

if selected_region:
  filtered_remotes = filtered_remotes[filtered_remotes["Region"].isin(selected_region)]
  filtered_keys = filtered_keys[filtered_keys["Region"].isin(selected_region)]

if selected_brand:
  filtered_remotes = filtered_remotes[filtered_remotes["Brand"].isin(selected_brand)]
  filtered_keys = filtered_keys[filtered_keys["Brand"].isin(selected_brand)]

if selected_device:
  filtered_remotes = filtered_remotes[filtered_remotes["Device"].isin(selected_device)]
  filtered_keys = filtered_keys[filtered_keys["Device"].isin(selected_device)]

# -----------------------------------------------------------------------------
# 5. Main Navigation Tabs
# -----------------------------------------------------------------------------
tab_analytics, tab_matcher, tab_finder = st.tabs(
    ["📊 Database Analytics", "🔍 Direct Signal Matcher", "📂 Smart Folder Finder"]
)

# =============================================================================
# TAB 1: DATABASE ANALYTICS
# =============================================================================
with tab_analytics:
  m1, m2, m3, m4, m5 = st.columns(5)
  m1.metric("Total Folders / Remotes", len(filtered_remotes))
  m2.metric("Total Keys / Signals", len(filtered_keys))
  m3.metric("Unique Brands", filtered_remotes["Brand"].nunique())
  m4.metric("Unique Device Types", filtered_remotes["Device"].nunique())
  m5.metric("Avg Keys / Remote", f"{filtered_remotes['Total Keys'].mean():.1f}" if len(filtered_remotes) > 0 else "0")
  st.divider()

  col1, col2 = st.columns(2)
  with col1:
    st.subheader("🏷️ Brand Statistics")
    brand_counts = filtered_remotes["Brand"].value_counts().reset_index()
    brand_counts.columns = ["Brand", "Count"]
    st.plotly_chart(px.bar(brand_counts, x="Brand", y="Count", text="Count", color="Brand", title="Remotes per Brand"), use_container_width=True)

  with col2:
    st.subheader("📺 Device Statistics")
    device_counts = filtered_remotes["Device"].value_counts().reset_index()
    device_counts.columns = ["Device", "Count"]
    st.plotly_chart(px.pie(device_counts, names="Device", values="Count", hole=0.4, title="Device Type Distribution"), use_container_width=True)

  st.divider()

  col3, col4 = st.columns(2)
  with col3:
    st.subheader("📡 Protocol Statistics")
    proto_counts = filtered_keys["Protocol"].value_counts().reset_index()
    proto_counts.columns = ["Protocol", "Total Keys"]
    st.plotly_chart(px.bar(proto_counts, x="Total Keys", y="Protocol", orientation="h", text="Total Keys", color="Protocol", title="Signals by IR Protocol"), use_container_width=True)

  with col4:
    st.subheader("🌍 Region & Country Coverage")
    region_counts = filtered_remotes.groupby(["Region", "Country"]).size().reset_index(name="Count")
    st.plotly_chart(px.sunburst(region_counts, path=["Region", "Country"], values="Count", title="Geographic Breakdown"), use_container_width=True)

  st.divider()

  st.subheader("🔌 Protocol-to-Brand Mapping Analytics")
  pb_col1, pb_col2 = st.columns(2)
  proto_brand_df = filtered_keys.groupby(["Protocol", "Brand"]).size().reset_index(name="Signal Count")
  with pb_col1:
    st.plotly_chart(px.bar(proto_brand_df, x="Protocol", y="Signal Count", color="Brand", title="Protocol Stacked by Brand", barmode="stack", text="Signal Count"), use_container_width=True)
  with pb_col2:
    st.plotly_chart(px.sunburst(proto_brand_df, path=["Brand", "Protocol"], values="Signal Count", title="Brand -> Protocol Breakdown"), use_container_width=True)

  st.markdown("#### 📋 Protocol vs. Brand Matrix")
  st.dataframe(pd.crosstab(filtered_keys["Protocol"], filtered_keys["Brand"], margins=True, margins_name="Total Signals"), use_container_width=True)
  st.divider()

  st.subheader("🔍 Signal Duplication & Brand Overlap Analysis")
  valid_keys = filtered_keys[filtered_keys["Protocol"] != "Unknown"]

  dup_tab1, dup_tab2 = st.tabs(["⚡ Cross-Brand Code Sharing", "🔁 Same-Remote Duplicate Commands"])
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
      st.warning(f"Found {len(same_remote_dups)} instances where a single remote uses identical Hex codes for multiple buttons.")
      st.dataframe(same_remote_dups, use_container_width=True, hide_index=True)
    else:
      st.info("No intra-remote key collisions detected.")

  st.divider()

  st.subheader("🗂️ Universal Hex Dictionary (Reverse Lookup)")
  st.markdown("Grouped strictly by Protocol, Address, and Command.")
  st.dataframe(compute_dictionary(valid_keys), use_container_width=True, hide_index=True)
  st.divider()

  st.subheader("🔄 Device-Brand Coverage Matrix")
  st.dataframe(pd.crosstab(filtered_remotes["Brand"], filtered_remotes["Device"], margins=True, margins_name="Total"), use_container_width=True)
  st.divider()

  st.subheader("📁 Processed Folders Explorer")
  e_tab1, e_tab2 = st.tabs(["Remote Folders Summary", "Detailed Signals & Decodes"])
  with e_tab1:
    st.dataframe(filtered_remotes, use_container_width=True, hide_index=True)
  with e_tab2:
    search_key = st.text_input("Filter signals by Key Name:")
    display_keys = filtered_keys
    if search_key:
      display_keys = display_keys[display_keys["Key Name"].str.contains(search_key, case=False, na=False)]
    st.dataframe(display_keys, use_container_width=True, hide_index=True)


# =============================================================================
# TAB 2: DIRECT SIGNAL MATCHER
# =============================================================================
with tab_matcher:
  st.header("🎯 Direct Raw Signal Matcher")
  st.write("Upload a raw signal file (`.SIG`, `.U1`, or `.U2`) or manually enter decodes to query the complete database across all folders.")

  input_method = st.radio("Select Input Mode:", ["Upload Signal File (.SIG / .U1 / .U2)", "Manual Hex Search"], horizontal=True)
  search_protocol, search_address, search_command = None, None, None

  if input_method == "Upload Signal File (.SIG / .U1 / .U2)":
    uploaded_signal = st.file_uploader("Upload a raw `.SIG`, `.U1`, or `.U2` file", type=["sig", "u1", "u2"], key="matcher_file_uploader")
    if uploaded_signal:
      ext = uploaded_signal.name.split(".")[-1].lower()
      with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(uploaded_signal.getvalue())
        tmp_path = tmp.name
      try:
        decoded = parse_and_decode_signal(tmp_path) if parse_and_decode_signal else None
        if decoded and isinstance(decoded, dict) and decoded.get("status") in ["Success", "Repeat"]:
          search_protocol = decoded.get("protocol")
          search_address = decoded.get("address")
          search_command = decoded.get("command")
          st.success(f"**Successfully Decoded File:** Protocol: `{search_protocol}`, Address: `{search_address}`, Command: `{search_command}`")
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
    st.write(f"**Protocol:** `{search_protocol or 'Any'}` | **Address:** `{search_address or 'Any'}` | **Command:** `{search_command or 'Any'}`")

    matches = df_keys.copy()
    if search_protocol:
      matches = matches[matches["Protocol"].astype(str).str.upper() == str(search_protocol).strip().upper()]
    if search_address:
      matches = matches[matches["Address"].astype(str).str.strip().str.lower() == str(search_address).strip().lower()]
    if search_command:
      matches = matches[matches["Command"].astype(str).str.strip().str.lower() == str(search_command).strip().lower()]

    st.subheader(f"📋 Exact Database Matches ({len(matches)} found)")
    if len(matches) > 0:
      output_cols = ["Folder ID", "Brand", "Device", "Model", "Key Name", "Protocol", "Address", "Command", "Country", "Region", "Source File"]
      st.dataframe(matches[output_cols].reset_index(drop=True), use_container_width=True)
    else:
      st.warning("No records matched the specified protocol and hex criteria.")

# =============================================================================
# TAB 3: SMART FOLDER FINDER
# =============================================================================
with tab_finder:
  st.header("📂 Smart Folder Finder")
  st.write("Find remote folders that contain a specific combination of keys for a target device. Adjust the tolerance slider if you don't need a 100% perfect match.")

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
        "Minimum Keys Match Tolerance",
        min_value=min_tol, max_value=max_tol, value=max_tol,
        help="Set the minimum number of requested keys a folder must have to be considered a match."
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
        cand_keys = df_keys[(df_keys["Folder ID"].isin(valid_folders)) & (df_keys["Key Name"].isin(req_keys))]

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
              matched_list = [k.strip() for k in matched_str.split(",")] if matched_str else []
              missing = set(req_keys) - set(matched_list)
              return ", ".join(sorted(missing)) if missing else "None (100% Match)"
            results["Missing Keys"] = results["Matched Keys"].apply(get_missing_keys)

            results = results.sort_values(by=["Matched Keys Count", "Brand"], ascending=[False, True])
            st.success(f"🎉 Found {len(results)} folders matching your criteria!")

            display_cols = ["Folder ID", "Brand", "Device", "Model", "Region", "Matched Keys Count", "Matched Keys", "Missing Keys"]
            st.dataframe(results[display_cols], use_container_width=True, hide_index=True)