import streamlit as st 

# 设置全局属性
st.set_page_config(
    page_title='我是标题',
    page_icon=' ',
    layout='wide'
)

# 正文
st.title('hello world')
st.markdown('> Streamlit 支持通过 st.markdown 直接渲染 markdown')