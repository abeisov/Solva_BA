import streamlit as st
from datetime import date
import re
import sqlite3
import smtplib
from email.mime.text import MIMEText

page_bg_css = """
<style>
    .stApp {
        background-color: #4e4fdf;
    }
</style>
"""

st.markdown(page_bg_css, unsafe_allow_html=True)

def get_db_connection():
    conn = sqlite3.connect('loans.db', check_same_thread=False)
    return conn

def create_table():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS loan_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            birth_date TEXT,
            email TEXT UNIQUE,
            phone TEXT UNIQUE,
            job_status TEXT,
            salary REAL,
            other_loans REAL
        )
    ''')
    conn.commit()
    conn.close()

create_table()

def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email)

def is_valid_phone(phone):
    phone_regex = r'^\+7\d{10}$'
    return re.match(phone_regex, phone)

def calculate_age(birth_date):
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def calculate_loan_offer(salary, other_loans):
    loan_amount = (salary - other_loans) * 10
    interest_rate = 0.03
    total_to_repay = loan_amount * (1 + interest_rate * 12)
    return loan_amount, total_to_repay

def is_existing_user(email, phone):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM loan_applications WHERE email = ? OR phone = ?', (email, phone))
    user_exists = c.fetchone()
    conn.close()
    return user_exists

def save_to_db(name, birth_date, email, phone, job_status, salary, other_loans):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO loan_applications (name, birth_date, email, phone, job_status, salary, other_loans)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, birth_date, email, phone, job_status, salary, other_loans))
    conn.commit()
    conn.close()

def send_email(recipient_email, subject, body):
    sender_email = st.secrets["SENDER_EMAIL"]
    sender_password = st.secrets["SENDER_PASSWORD"]

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
    except Exception as e:
        print('Не удалось отправить электронное письмо:', e)

def loan_application():
    st.title("Заявка на годовой займ")

    min_birth_date = date(1900, 1, 1)
    max_birth_date = date.today()

    name = st.text_input("Введите ваше имя")
    birth_date = st.date_input("Дата рождения", min_value=min_birth_date, max_value=max_birth_date)
    email = st.text_input("Введите ваш email")
    phone = st.text_input("Введите ваш телефон", value="+7")
    job_status = st.selectbox("Ваш статус занятости", ["Работающий", "Безработный"])

    salary = st.text_input("Введите вашу месячную зарплату", value="")
    other_loans = st.text_input("Ежемесячные выплаты по другим кредитам", value="")

    if st.button("Отправить заявку"):
        if not is_valid_email(email):
            st.error("Пожалуйста, введите корректный адрес электронной почты.")
            return
        if not is_valid_phone(phone):
            st.error("Пожалуйста, введите корректный номер телефона в формате +7XXXXXXXXXX (10 цифр после кода страны).")
            return

        if is_existing_user(email, phone):
            st.error("Пользователь с таким номером телефона или email уже существует в базе данных.")
            return

        try:
            salary = float(salary)
            other_loans = float(other_loans)

            save_to_db(name, birth_date, email, phone, job_status, salary, other_loans)

            age = calculate_age(birth_date)
            if age < 18 or age > 90:
                st.session_state['result'] = "Простите, мы не можем вам помочь. Ваш возраст не соответствует условиям."
                st.session_state['success'] = False
                subject = "Ваш займ отклонен"
                body = "К сожалению, ваш запрос на займ был отклонен. Причина: Ваш возраст не соответствует условиям."
                send_email(email, subject, body)
                st.session_state['page'] = 'result'
                st.experimental_rerun()
            elif salary < 100:
                st.session_state['result'] = "Простите, мы не можем вам помочь. Зарплата слишком низкая."
                st.session_state['success'] = False
                subject = "Ваш займ отклонен"
                body = "К сожалению, ваш запрос на займ был отклонен. Причина: Зарплата слишком низкая."
                send_email(email, subject, body)
                st.session_state['page'] = 'result'
                st.experimental_rerun()
            elif job_status == "Безработный":
                st.session_state['result'] = "Простите, мы не можем вам помочь. Для получения займа необходимо иметь работу."
                st.session_state['success'] = False
                subject = "Ваш займ отклонен"
                body = "К сожалению, ваш запрос на займ был отклонен. Причина: Необходимо иметь работу для получения займа."
                send_email(email, subject, body)
                st.session_state['page'] = 'result'
                st.experimental_rerun()
            else:
                loan_amount, total_to_repay = calculate_loan_offer(salary, other_loans)
                st.session_state['loan_amount'] = loan_amount
                st.session_state['total_to_repay'] = total_to_repay

                st.session_state['result'] = f"Ваш займ готов! Мы готовы выдать вам {loan_amount:.2f} рублей на 1 год."
                st.session_state['success'] = True

                subject = "Ваш займ одобрен"
                body = f"Поздравляем, ваш займ на сумму {loan_amount:.2f} рублей одобрен. Вы должны вернуть {total_to_repay:.2f} рублей. Для получения денег, пожалуйста, позвоните по телефону +77012345678."
                send_email(email, subject, body)
                st.session_state['page'] = 'result'
                st.experimental_rerun()
        except ValueError:
            st.error("Пожалуйста, введите корректные числовые значения для зарплаты и выплат по кредитам.")

def loan_result():
    st.title("Результат заявки на займ")

    result_message = st.session_state['result']
    loan_amount = st.session_state.get('loan_amount', 0)
    total_to_repay = st.session_state.get('total_to_repay', 0)
    success = st.session_state['success']

    if success:
        st.success(result_message)
        st.info(f"Вы должны вернуть {total_to_repay:.2f} рублей.")
        st.info(f"Для получения денег, пожалуйста, позвоните по телефону +77012345678")
    else:
        st.error(result_message)

    if st.button("Вернуться назад"):
        st.session_state['page'] = 'application'
        st.experimental_rerun()

if 'page' not in st.session_state:
    st.session_state['page'] = 'application'

if st.session_state['page'] == 'application':
    loan_application()
elif st.session_state['page'] == 'result':
    loan_result()