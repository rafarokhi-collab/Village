import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# تنظیمات صفحه
st.set_page_config(page_title="بانک اطلاعاتی روستاها", layout="wide", page_icon="🏡")

DB_NAME = "village_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS villages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        province TEXT,
        county TEXT,
        district TEXT,
        population INTEGER,
        households INTEGER,
        dehyar_name TEXT,
        dehyar_phone TEXT,
        created_at TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS custom_fields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        field_name TEXT NOT NULL UNIQUE,
        category TEXT DEFAULT 'عمومی'
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS custom_field_values (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        village_id INTEGER,
        field_id INTEGER,
        value TEXT,
        FOREIGN KEY(village_id) REFERENCES villages(id) ON DELETE CASCADE,
        FOREIGN KEY(field_id) REFERENCES custom_fields(id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    conn.close()

init_db()

# عنوان سامانه
st.title("🏡 سامانه جامع بانک اطلاعاتی روستاها")

# منوی منوی کناری (Sidebar)
menu = ["📊 مشاهده و گزارش‌گیری", "➕ ثبت روستای جدید", "⚙️️ مدیریت فیلدهای پویا", "📥/📤 اکسل و پشتیبان"]
choice = st.sidebar.selectbox("منوی اصلی", menu)

# ۱. بخش مشاهده و گزارش‌گیری
if choice == "📊 مشاهده و گزارش‌گیری":
    st.subheader("جدول اطلاعات روستاها و فیلتر پیشرفته")
    
    col1, col2 = st.columns(2)
    with col1:
        search_name = st.text_input("جستجو بر اساس نام روستا یا دهیار:")
    with col2:
        search_province = st.text_input("جستجو بر اساس استان:")

    conn = sqlite3.connect(DB_NAME)
    query = "SELECT * FROM villages WHERE 1=1"
    params = []
    
    if search_name:
        query += " AND (name LIKE ? OR dehyar_name LIKE ?)"
        params.extend([f"%{search_name}%", f"%{search_name}%"])
    if search_province:
        query += " AND province LIKE ?"
        params.append(f"%{search_province}%")
        
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    st.dataframe(df, use_container_width=True)

# ۲. بخش ثبت روستای جدید
elif choice == "➕ ثبت روستای جدید":
    st.subheader("ثبت اطلاعات روستای جدید")
    
    with st.form("add_village_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("نام روستا *")
            province = st.text_input("استان")
            county = st.text_input("شهرستان")
            district = st.text_input("بخش")
        with col2:
            population = st.number_input("جمعیت (نفر)", min_value=0, step=1)
            households = st.number_input("تعداد خانوار", min_value=0, step=1)
            dehyar_name = st.text_input("نام دهیار")
            dehyar_phone = st.text_input("شماره تلفن دهیار")

        # بارگذاری فیلدهای پویا
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, field_name, category FROM custom_fields")
        custom_fields = cursor.fetchall()
        
        st.write("---")
        st.write("**فیلدهای سفارشی و تکمیلی:**")
        custom_inputs = {}
        for f_id, f_name, f_cat in custom_fields:
            custom_inputs[f_id] = st.text_input(f"{f_name} ({f_cat})")

        submitted = st.form_submit_button("💾 ثبت روستا")
        
        if submitted:
            if not name:
                st.error("ورود نام روستا الزامی است!")
            else:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                cursor.execute("""
                    INSERT INTO villages (name, province, county, district, population, households, dehyar_name, dehyar_phone, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, province, county, district, population, households, dehyar_name, dehyar_phone, now_str))
                
                v_id = cursor.lastrowid
                for f_id, val in custom_inputs.items():
                    if val:
                        cursor.execute("INSERT INTO custom_field_values (village_id, field_id, value) VALUES (?, ?, ?)", (v_id, f_id, val))
                        
                conn.commit()
                conn.close()
                st.success(f"روستای {name} با موفقیت ثبت شد.")

# ۳. مدیریت فیلدهای پویا
elif choice == "⚙️ مدیریت فیلدهای پویا":
    st.subheader("تعریف فیلدهای جدید (منوها)")
    
    new_field = st.text_input("نام فیلد جدید (مثلاً: وضعیت آب شرب):")
    category = st.text_input("دسته‌بندی (مثلاً: زیرساخت، آموزش، بهداشت):", value="عمومی")
    
    if st.button("➕ افزودن فیلد"):
        if new_field:
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO custom_fields (field_name, category) VALUES (?, ?)", (new_field, category))
                conn.commit()
                conn.close()
                st.success(f"فیلد '{new_field}' با موفقیت اضافه شد.")
            except:
                st.error("این فیلد قبلاً تعریف شده است.")

# ۴. خروجی اکسل و پشتیبان‌گیری
elif choice == "📥/📤 اکسل و پشتیبان":
    st.subheader("دریافت خروجی اکسل و پشتیبان‌گیری")
    
    conn = sqlite3.connect(DB_NAME)
    df_all = pd.read_sql_query("SELECT * FROM villages", conn)
    conn.close()
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_all.to_excel(writer, index=False, sheet_name='Villages')
        
    st.download_button(
        label="📊 دانلود فایل اکسل روستاها",
        data=buffer.getvalue(),
        file_name=f"villages_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )

