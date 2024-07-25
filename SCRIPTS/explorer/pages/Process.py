import json
from pathlib import Path

import pandas as pd

import streamlit as st

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from const import INPUT_DATA_PATH, OUTPUT_DATA_PATH

st.set_page_config(page_title="(deprecated) Cone Data Processor", page_icon="📊")

st.title("(deprecated) Cone Data Processor")

# Get the paths to all the test files
test_name_map = {p.stem: p for p in list(INPUT_DATA_PATH.rglob("*.csv"))}

# Get the paths to all the metadata files
metadata_name_map = {p.stem: p for p in list(INPUT_DATA_PATH.rglob("*.json"))}


# Initialize some session state variables
if "columns" not in st.session_state:
    st.session_state.columns = []
if "index" not in st.session_state:
    st.session_state.index = 0

if "current_test_edited" not in st.session_state:
    st.session_state.current_test_edited = False


st.subheader(list(test_name_map.keys())[st.session_state.index])

# Progress bar
processed_files = len(list(OUTPUT_DATA_PATH.rglob("*.csv")))
progress_bar = st.progress(
    processed_files / len(test_name_map),
    text=f"Test {processed_files} of {len(test_name_map)}",
)


# File controls
def next_file():
    if st.session_state.index + 1 >= len(test_name_map):
        return
    st.session_state.index += 1

    st.session_state.current_test_edited = False


def prev_file():
    if st.session_state.index - 1 < 0:
        return
    st.session_state.index -= 1

    st.session_state.current_test_edited = False


def set_file():
    st.session_state.index = list(test_name_map.values()).index(
        test_name_map[file_selection]
    )

    st.session_state.current_test_edited = False


col1, col2 = st.columns(2)
col1.button("Previous file", use_container_width=True, on_click=prev_file)
col2.button("Next file", use_container_width=True, on_click=next_file)

col3, col4 = st.columns([0.8, 0.2], vertical_alignment="bottom")
file_selection = col3.selectbox(
    "Select test",
    list(test_name_map.keys()),
    index=st.session_state.index,
)
col4.button("Go", on_click=set_file, use_container_width=True)

test_data = pd.read_csv(
    test_name_map[list(test_name_map.keys())[st.session_state.index]]
).set_index("Time (s)")

test_metadata = json.load(
    open(metadata_name_map[list(test_name_map.keys())[st.session_state.index]])
)

if not st.session_state.current_test_edited:
    st.session_state.current_data = pd.read_csv(
        test_name_map[list(test_name_map.keys())[st.session_state.index]]
    ).set_index("Time (s)")
    st.session_state.current_metadata = json.load(
        open(metadata_name_map[list(test_name_map.keys())[st.session_state.index]])
    )


def get_metadata():
    return st.session_state.current_metadata


def set_metadata(metadata):
    st.session_state.current_metadata = metadata
    st.session_state.current_test_edited = True


def get_data():
    return st.session_state.current_data


def set_data(data):
    st.session_state.current_data = data
    st.session_state.current_test_edited = True


def save_data():
    get_data().to_csv(
        OUTPUT_DATA_PATH
        / Path(list(test_name_map.keys())[st.session_state.index]).with_suffix(".csv")
    )


def save_metadata():
    json.dump(
        get_metadata(),
        open(
            OUTPUT_DATA_PATH
            / Path(list(test_name_map.keys())[st.session_state.index]).with_suffix(
                ".json"
            ),
            "w",
        ),
        indent=4,
    )


def save_test():
    save_data()
    save_metadata()
    next_file()


col5, col6 = st.columns([0.7, 0.3])

col5.button(
    "Save test and continue",
    on_click=save_test,
    use_container_width=True,
    type="primary",
)


def reload():
    st.session_state.current_test_edited = False


col6.button("Reload", on_click=lambda: reload(), use_container_width=True)

# if the current file is already processed, show a notice
if Path(
    OUTPUT_DATA_PATH
    / Path(list(test_name_map.keys())[st.session_state.index]).with_suffix(".csv")
).exists():
    st.info("This file has already been processed!")

st.divider()

st.markdown("#### View data")
columns_to_graph = st.multiselect(
    "Select column(s) from test to graph",
    options=test_data.columns,
    max_selections=2,
)

fig = make_subplots(specs=[[{"secondary_y": True}]])
if len(columns_to_graph) >= 1:
    fig.add_trace(
        go.Scatter(y=test_data[columns_to_graph[0]], name=columns_to_graph[0])
    )
    fig.update_yaxes(title_text=columns_to_graph[0], secondary_y=False)
    if len(columns_to_graph) == 2:
        fig.add_trace(
            go.Scatter(
                y=test_data[columns_to_graph[1]], name=columns_to_graph[1] + " (sec.)"
            ),
            secondary_y=True,
        )
        fig.update_yaxes(title_text=columns_to_graph[1], secondary_y=True)

st.plotly_chart(fig)

with st.expander("**View data in table format**"):
    st.dataframe(test_data, use_container_width=True)

st.divider()


def make_metadata_df():
    # since streamlit's data editor requires all rows in a column to have the same type, we'll convert everything to strings.
    converted_metadata = {k: str(v or "") for k, v in get_metadata().items()}
    converted_metadata = pd.DataFrame(
        converted_metadata.items(), columns=["property", "value"]
    ).set_index("property")
    return converted_metadata


# now, convert the strings back into the correct types
def fix_types(key, value):

    try:
        original_type = type(test_metadata[key])
    except:
        original_type = type(get_metadata()[key])
    try:
        if value in [""]:
            return (key, None)
        if original_type is int:
            return (key, int(value))
        elif original_type is float:
            return (key, float(value))
        elif original_type is bool:
            if value.lower() == "true":
                return (key, True)
            elif value.lower() == "false":
                return (key, False)
            return (key, None)
        elif original_type is str:
            return (key, str(value))
        else:
            try:
                return (key, float(value))
            except:
                pass
            try:
                return (key, int(value))
            except:
                pass
            try:
                if value.lower() == "true":
                    return (key, True)
                elif value.lower() == "false":
                    return (key, False)
            except:
                pass
            try:
                return (key, str(value))
            except:
                pass

            return (key, None)

    except Exception as e:
        st.error(f"Type conversion was not successful for {key}: {e}")
        return (key, None)


st.markdown("#### Edit metadata")

st.markdown(
    "Metadata file is updated automatically. Leave the cell empty for `None` and use `True` and `False` for their respective Boolean equivalents."
)

metadata_df = make_metadata_df()
edited_metadata = st.data_editor(
    metadata_df,
    use_container_width=True,
).to_dict()["value"]

edited_metadata = dict(map(lambda kv: fix_types(kv[0], kv[1]), edited_metadata.items()))

set_metadata(edited_metadata)

# r = get_metadata()
# r["report_citation_key"] = st.text_input("Report citation key (BibTeX)")
# set_metadata(r)

st.markdown("#### :red[Danger zone]")

st.markdown(
    "*Note: Because changes are applied only to the copy saved to the output folder, the original remains unmodified, meaning that any changes made in this section will **not** be reflected in other sections of the app.*"
)

tab1, tab2, tab3 = st.tabs(
    ["Replace columns with null values", "Delete columns", "Delete test"]
)

with tab1:
    columns_to_delete = st.multiselect(
        "Select column(s) to replace with null values",
        options=test_data.columns,
    )

    # replaces columns with null values
    def null_columns():
        for column in columns_to_delete:
            test_data[column] = None
            set_data(test_data)
        st.success("Columns replaced with null values")

    st.button("Replace columns", on_click=null_columns)

with tab2:
    columns_to_delete = st.multiselect(
        "Select column(s) to delete",
        options=test_data.columns,
    )

    def delete_columns():
        for column in columns_to_delete:
            del test_data[column]
        set_data(test_data)
        st.success("Columns deleted")

    st.button("Delete columns", on_click=delete_columns)

with tab3:

    def delete_test():
        # # if the test file exists, delete it
        if test_name_map[list(test_name_map.keys())[st.session_state.index]].exists():
            test_name_map[list(test_name_map.keys())[st.session_state.index]].unlink()
        # if the metadata file exists, delete it
        if metadata_name_map[
            list(test_name_map.keys())[st.session_state.index]
        ].exists():
            metadata_name_map[
                list(test_name_map.keys())[st.session_state.index]
            ].unlink()

        # if either of the output files exist, delete them
        if (
            OUTPUT_DATA_PATH
            / Path(list(test_name_map.keys())[st.session_state.index]).with_suffix(
                ".csv"
            )
        ).exists():
            (
                OUTPUT_DATA_PATH
                / Path(list(test_name_map.keys())[st.session_state.index]).with_suffix(
                    ".csv"
                )
            ).unlink()
        if (
            OUTPUT_DATA_PATH
            / Path(list(test_name_map.keys())[st.session_state.index]).with_suffix(
                ".json"
            )
        ).exists():
            (
                OUTPUT_DATA_PATH
                / Path(list(test_name_map.keys())[st.session_state.index]).with_suffix(
                    ".json"
                )
            ).unlink()

        st.error("Test deleted")
        next_file()

    st.markdown(
        "**Note: the original (input) file AND the output file generated by this app are deleted.**"
    )
    st.button(
        "Delete output & continue to next test", on_click=delete_test, type="primary"
    )