import gzip
import json
import os
import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="IR Remote Signal Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 IR Remote Signal Database Analytics")
st.caption("Insights, coverage metrics, and protocol breakdowns across processed remote folders.")

# -----------------------------------------------------------------------------
# 2. Data Loading & Parsing Function
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_parse_json(file_source):
  # 1. Parse JSON from file path string or uploaded file
  if isinstance(file_source, str):
    if file_source.endswith('.gz'):
      with gzip.open(file_source, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    else:
      with open(file_source, 'r', encoding='utf-8') as f:
        data = json.load(f)
  else:
    # Handles uploaded file objects in Streamlit
    if hasattr(file_source, 'name') and file_source.name.endswith('.gz'):
      with gzip.open(file_source, 'rt') as f:
        data = json.load(f)
    else:
      data = json.load(file_source)

  remotes = data.get('remotes', {})

  remote_summary = []
  key_signals = []

  for folder_id, remote_data in remotes.items():
    meta = remote_data.get('metadata', {})
    keys = remote_data.get('keys', {})

    brand = meta.get('brand') or 'Unknown'
    device = meta.get('device') or 'Unknown'
    subdevice = meta.get('subdevice') or 'N/A'
    model = meta.get('model') or 'N/A'
    devicemodel = meta.get('devicemodel') or 'N/A'
    country = meta.get('country') or 'Unknown'
    region = meta.get('region') or 'Unknown'

    # Record Folder Level Summary
    remote_summary.append({
        'Folder ID': folder_id,
        'Brand': brand,
        'Device': device,
        'Subdevice': subdevice,
        'Model': model,
        'Device Model': devicemodel,
        'Country': country,
        'Region': region,
        'Total Keys': len(keys),
    })

    # Record Key Level Data
    for key_name, key_info in keys.items():
      decode = key_info.get('decode_data', {})

      # Handle cases where decode_data is a list
      if isinstance(decode, list):
        decode = decode[0] if len(decode) > 0 else {}

      key_signals.append({
          'Folder ID': folder_id,
          'Brand': brand,
          'Device': device,
          'Model': model,
          'Region': region,
          'Country': country,
          'Key Name': key_name,
          'Protocol': decode.get('protocol', 'Unknown'),
          'Address': decode.get('address', 'N/A'),
          'Command': decode.get('command', 'N/A'),
          'Payload': decode.get('payload', 'N/A'),
          'Source File': key_info.get('source_file', ''),
      })

  df_remotes = pd.DataFrame(remote_summary)
  df_keys = pd.DataFrame(key_signals)

  # CRITICAL: Return the DataFrames so dashboard.py can unpack them
  return df_remotes, df_keys
# -----------------------------------------------------------------------------
# 3. Sidebar Data Selection & Filtering
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Data Options & Filters")

# File Path Definitions
json_gz_path = "batch_passed.json.gz"
json_path = "batch_passed.json"

# Sidebar file uploader
uploaded_file = st.sidebar.file_uploader(
    "Upload custom JSON or GZ", type=["json", "gz"]
)

# File Selection Logic
if uploaded_file is not None:
  df_remotes, df_keys = load_and_parse_json(uploaded_file)
elif os.path.exists(json_gz_path):
  df_remotes, df_keys = load_and_parse_json(json_gz_path)
elif os.path.exists(json_path):
  df_remotes, df_keys = load_and_parse_json(json_path)
else:
  st.error("No dataset found! Please ensure batch_passed.json or batch_passed.json.gz is in the project folder.")
  st.stop()

# Sidebar Filters
st.sidebar.subheader("Filter Dashboard")
selected_region = st.sidebar.multiselect("Region", options=sorted(df_remotes["Region"].unique()))
selected_brand = st.sidebar.multiselect("Brand", options=sorted(df_remotes["Brand"].unique()))
selected_device = st.sidebar.multiselect("Device", options=sorted(df_remotes["Device"].unique()))

# Apply Filters
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
# 4. Top Metric KPIs
# -----------------------------------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Folders / Remotes", len(filtered_remotes))
m2.metric("Total Keys / Signals", len(filtered_keys))
m3.metric("Unique Brands", filtered_remotes["Brand"].nunique())
m4.metric("Unique Device Types", filtered_remotes["Device"].nunique())
m5.metric("Avg Keys / Remote", f"{filtered_remotes['Total Keys'].mean():.1f}" if len(filtered_remotes) > 0 else "0")

st.divider()

# -----------------------------------------------------------------------------
# 5. Core Visualizations Section
# -----------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏷️ Brand Statistics")
    brand_counts = filtered_remotes["Brand"].value_counts().reset_index()
    brand_counts.columns = ["Brand", "Count"]
    fig_brand = px.bar(brand_counts, x="Brand", y="Count", text="Count", color="Brand",
                       title="Remotes per Brand")
    st.plotly_chart(fig_brand, use_container_width=True)

with col2:
    st.subheader("📺 Device Statistics")
    device_counts = filtered_remotes["Device"].value_counts().reset_index()
    device_counts.columns = ["Device", "Count"]
    fig_device = px.pie(device_counts, names="Device", values="Count", hole=0.4,
                        title="Device Type Distribution")
    st.plotly_chart(fig_device, use_container_width=True)

st.divider()

col3, col4 = st.columns(2)

with col3:
    st.subheader("📡 Protocol Statistics")
    proto_counts = filtered_keys["Protocol"].value_counts().reset_index()
    proto_counts.columns = ["Protocol", "Total Keys"]
    fig_proto = px.bar(proto_counts, x="Total Keys", y="Protocol", orientation="h", text="Total Keys",
                       color="Protocol", title="Signals by IR Protocol")
    st.plotly_chart(fig_proto, use_container_width=True)

with col4:
    st.subheader("🌍 Region & Country Coverage")
    region_counts = filtered_remotes.groupby(["Region", "Country"]).size().reset_index(name="Count")
    fig_region = px.sunburst(region_counts, path=["Region", "Country"], values="Count",
                             title="Geographic Breakdown (Region -> Country)")
    st.plotly_chart(fig_region, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 6. Protocol-to-Brand Mapping Section
# -----------------------------------------------------------------------------
st.subheader("🔌 Protocol-to-Brand Mapping Analytics")

pb_col1, pb_col2 = st.columns(2)
proto_brand_df = filtered_keys.groupby(["Protocol", "Brand"]).size().reset_index(name="Signal Count")

with pb_col1:
    fig_proto_brand_bar = px.bar(
        proto_brand_df,
        x="Protocol",
        y="Signal Count",
        color="Brand",
        title="Protocol Distribution Stacked by Brand",
        barmode="stack",
        text="Signal Count"
    )
    st.plotly_chart(fig_proto_brand_bar, use_container_width=True)

with pb_col2:
    fig_brand_proto_sunburst = px.sunburst(
        proto_brand_df,
        path=["Brand", "Protocol"],
        values="Signal Count",
        title="Brand -> Protocol Hierarchy Breakdown"
    )
    st.plotly_chart(fig_brand_proto_sunburst, use_container_width=True)

st.markdown("#### 📋 Protocol vs. Brand Matrix")
pb_crosstab = pd.crosstab(
    filtered_keys["Protocol"], 
    filtered_keys["Brand"], 
    margins=True, 
    margins_name="Total Signals"
)
st.dataframe(pb_crosstab, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 7. Hex Code Duplication & Cross-Brand Overlap Analysis
# -----------------------------------------------------------------------------
st.subheader("🔍 Signal Duplication & Brand Overlap Analysis")

# Standardize Hex Signature
valid_keys = filtered_keys[filtered_keys["Protocol"] != "Unknown"].copy()

def build_hex_sig(row):
    p = str(row["Protocol"])
    a = str(row["Address"])
    c = str(row["Command"])
    pl = str(row["Payload"])
    
    if a != "N/A" and c != "N/A":
        return f"{p} | Addr: {a} | Cmd: {c}"
    elif pl != "N/A":
        return f"{p} | Payload: {pl}"
    else:
        return f"{p} | Addr: {a} | Cmd: {c}"

valid_keys["Signal Code"] = valid_keys.apply(build_hex_sig, axis=1)

dup_tab1, dup_tab2 = st.tabs(["⚡ Cross-Brand Code Sharing", "🔁 Same-Remote Duplicate Commands"])

with dup_tab1:
    st.markdown("##### Signals Shared Across Multiple Brands (Potential Shared OEMs/IC Chipsets)")
    cross_brand = valid_keys.groupby("Signal Code").agg(
        Unique_Brands=("Brand", "nunique"),
        Brand_Names=("Brand", lambda x: ", ".join(sorted(set(x)))),
        Remotes_Count=("Folder ID", "nunique"),
        Folders=("Folder ID", lambda x: ", ".join(sorted(set(x)))),
        Keys_Mapped=("Key Name", lambda x: ", ".join(sorted(set(x)))),
        Total_Signals=("Key Name", "count")
    ).reset_index()

    shared_signals = cross_brand[cross_brand["Unique_Brands"] > 1].sort_values(by="Unique_Brands", ascending=False)

    if len(shared_signals) > 0:
        st.success(f"Found {len(shared_signals)} unique Hex signal signatures shared across different brands.")
        st.dataframe(shared_signals, use_container_width=True, hide_index=True)
    else:
        st.info("No cross-brand hex code overlaps detected in current filtered dataset.")

with dup_tab2:
    st.markdown("##### Duplicate Hex Commands Within the Same Remote Folder")
    intra_remote = valid_keys.groupby(["Folder ID", "Brand", "Signal Code"]).agg(
        Duplicate_Key_Count=("Key Name", "count"),
        Buttons_Sharing_Code=("Key Name", lambda x: ", ".join(x))
    ).reset_index()

    same_remote_dups = intra_remote[intra_remote["Duplicate_Key_Count"] > 1].sort_values(by="Duplicate_Key_Count", ascending=False)

    if len(same_remote_dups) > 0:
        st.warning(f"Found {len(same_remote_dups)} instances where a single remote uses identical Hex codes for multiple buttons.")
        st.dataframe(same_remote_dups, use_container_width=True, hide_index=True)
    else:
        st.info("No intra-remote key collisions detected in current filtered dataset.")

st.divider()

# -----------------------------------------------------------------------------
# 8. NEW: Universal Hex Dictionary (Protocol -> Hex -> Details Tree)
# -----------------------------------------------------------------------------
st.subheader("🗂️ Universal Hex Dictionary (Reverse Lookup)")
st.markdown("Grouped strictly by Protocol, Address, and Command. Use this to instantly see every single device, model, and key that belongs to a specific Hex code.")

# Group by the specific protocol components requested, dropping Unknowns
dictionary_df = valid_keys.groupby(["Protocol", "Address", "Command", "Payload"]).agg(
    Total_Occurrences=("Key Name", "count"),
    Brands=("Brand", lambda x: ", ".join(sorted(set(x)))),
    Devices=("Device", lambda x: ", ".join(sorted(set(x)))),
    Models=("Model", lambda x: ", ".join(sorted(set([str(m) for m in x if str(m) != "N/A"])))),
    Folders=("Folder ID", lambda x: ", ".join(sorted(set(x)))),
    Mapped_Keys=("Key Name", lambda x: ", ".join(sorted(set(x))))
).reset_index()

# Sort by the most utilized codes
dictionary_df = dictionary_df.sort_values(by="Total_Occurrences", ascending=False)

st.dataframe(
    dictionary_df,
    use_container_width=True,
    hide_index=True
)

st.divider()

# -----------------------------------------------------------------------------
# 9. Device-Brand Matrix (Crosstab)
# -----------------------------------------------------------------------------
st.subheader("🔄 Device-Brand Coverage Matrix")
crosstab = pd.crosstab(filtered_remotes["Brand"], filtered_remotes["Device"], margins=True, margins_name="Total")
st.dataframe(crosstab, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 10. Folder & Signal Exploration Table
# -----------------------------------------------------------------------------
st.subheader("📁 Processed Folders Explorer")

tab1, tab2 = st.tabs(["Remote Folders Summary", "Detailed Signals & Decodes"])

with tab1:
    st.dataframe(filtered_remotes, use_container_width=True, hide_index=True)

with tab2:
    search_key = st.text_input("Filter signals by Key Name (e.g. Power, Volume, Play):")
    display_keys = filtered_keys
    if search_key:
        display_keys = display_keys[display_keys["Key Name"].str.contains(search_key, case=False, na=False)]
    st.dataframe(display_keys, use_container_width=True, hide_index=True)