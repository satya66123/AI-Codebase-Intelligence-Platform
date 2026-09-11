import streamlit as st

from app import Application
from app.config import settings
from app.presentation import render


st.set_page_config(
    page_title=settings.app_name,
    page_icon="🤖",
    layout="wide",
)


application = Application()
application.start()

render(application.container)