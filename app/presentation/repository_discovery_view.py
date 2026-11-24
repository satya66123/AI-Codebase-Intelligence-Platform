
from dataclasses import asdict, is_dataclass

import streamlit as st


SESSION_RESULT_KEY = "repository_discovery_result"


def render_repository_discovery_view(service):
    """Render the repository discovery interface."""

    st.header("Repository Discovery")
    st.caption(
        "Explore repository structure, files, languages and metadata."
    )

    repository_path = st.text_input(
        "Local repository path",
        placeholder="C:/Users/user/PycharmProjects/my-project",
        key="repository_discovery_path",
    )

    if st.button(
        "Discover Repository",
        key="discover_repository_button",
    ):
        if not repository_path.strip():
            st.error("Please enter a repository path.")
        else:
            try:
                result = service.discover(repository_path)

                st.session_state[SESSION_RESULT_KEY] = result

                st.success("Repository discovery completed.")

            except Exception as exc:
                st.error(f"Repository discovery failed: {exc}")

    result = st.session_state.get(SESSION_RESULT_KEY)

    if result is None:
        st.info("Enter a repository path to begin discovery.")
        return

    # Restore repository state after Streamlit reruns.
    service.restore_result(result)

    metadata = result.metadata

    st.subheader("Repository Overview")

    st.write("Repository:", result.repository.name)
    st.write("Location:", str(result.repository.root))

    st.metric("Total Files", metadata["total_files"])
    st.metric("Total Directories", metadata["total_directories"])
    st.metric("Total Size (Bytes)", metadata["total_size_bytes"])

    st.subheader("Programming Languages")
    st.json(metadata["languages"])

    st.subheader("Repository Structure")
    st.code(result.repository_map, language="text")

    st.subheader("File Metadata")

    file_rows = [
        asdict(item) if is_dataclass(item) else item
        for item in metadata["files"]
    ]

    if file_rows:
        st.dataframe(
            file_rows,
            use_container_width=True,
        )
    else:
        st.info("No files were discovered.")

    st.subheader("Search Repository Files")

    search_query = st.text_input(
        "Search by filename, path, extension or language",
        key="repository_discovery_search",
    )

    if search_query.strip():
        try:
            search_results = service.search_files(search_query)

            st.write(f"Matching files: {len(search_results)}")

            if search_results:
                st.dataframe(
                    search_results,
                    use_container_width=True,
                )
            else:
                st.info("No matching files found.")

        except Exception as exc:
            st.error(f"Repository search failed: {exc}")
