import streamlit as st

from appy import Application
from appy.config import settings
from appy.presentation import render


st.set_page_config(
    page_title=settings.app_name,
    page_icon="🤖",
    layout="wide",
)


application = Application()
application.start()

render(application.container)