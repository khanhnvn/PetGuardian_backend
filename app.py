from flask import Flask, request, jsonify, session, send_from_directory, redirect, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import os
from passlib.hash import bcrypt 
from flask_cors import CORS
from functools import wraps
from flask_mail import Mail, Message
import random
import string
import math
import locale
from payos import PaymentData, ItemData, PayOS
from dotenv import load_dotenv
import json
from datetime import datetime

app = Flask(__name__, static_folder='../frontend/public')
app.secret_key = 'your secret key' 

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456' 
app.config['MYSQL_DB'] = 'geeklogin'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

CORS(app)

mysql = MySQL(app)

# frontend_folder = os.path.join(os.getcwd(),"..","frontend")
# dist_folder = os.path.join(frontend_folder,"dist")

# # server static files from the "dist" folder under the frontend directory
# @app.route("/",defaults={"filename":""})
# @app.route("/<path:filename>")
# def index(filename):
#     if not filename:
#         filename = "index.html"
#     return send_from_directory(dist_folder,filename)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ngodangtranhoan@gmail.com'  # Thay bằng địa chỉ email của bạn
app.config['MAIL_PASSWORD'] = 'pezj jetj ohwj cnnr'     # Thay bằng App Password
app.config['MAIL_DEFAULT_SENDER'] = ('PetGuardian', 'your-email@gmail.com')
app.config['MAIL_DEBUG'] = True  # Bật debug cho Flask-Mail

mail = Mail(app)

# Load environment variables from .env file
load_dotenv()

# Khởi tạo PayOS SDK
payos = PayOS(
    client_id=os.environ.get('PAYOS_CLIENT_ID'),
    api_key=os.environ.get('PAYOS_API_KEY'),
    checksum_key=os.environ.get('PAYOS_CHECKSUM_KEY')
)

# Thiết lập locale cho Việt Nam
locale.setlocale(locale.LC_ALL, 'vi_VN.UTF-8')


# === Hàm helper ===

def send_verification_email(to_email, verification_code):
    try:
        msg = Message("Pet Guardian - Mã xác thực",
                      sender=app.config['MAIL_DEFAULT_SENDER'],
                      recipients=[to_email])
        msg.body = f"Mã xác thực của bạn là: {verification_code}"
        mail.send(msg)
        print("Verification email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' in session:
            return f(*args, **kwargs)
        return jsonify({'message': 'Bạn cần đăng nhập'}), 401
    return decorated_function

def hash_password(password):
    return bcrypt.hash(password)

def verify_password(password, hashed_password):
    return bcrypt.verify(password, hashed_password)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_currency(amount):
  """Định dạng số tiền thành VND."""
  amount = math.floor(amount / 1000) * 1000
  return locale.currency(amount, grouping=True, symbol=True)


# === API endpoints cho login/register ===

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        role_id = data.get('role_id')
        
        # Kiểm tra dữ liệu đầu vào
        if not username or not password or not email:
            return jsonify({'message': 'Vui lòng điền đầy đủ thông tin'}), 400
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            return jsonify({'message': 'Email không hợp lệ'}), 400
        if not re.match(r'[A-Za-z0-9]+', username):
            return jsonify({'message': 'Tên đăng nhập chỉ được chứa chữ cái và số'}), 400

        hashed_pass = hash_password(password)

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
            account = cursor.fetchone()
            if account:
                return jsonify({'message': 'Tài khoản đã tồn tại'}), 409
            else:
                cursor.execute('INSERT INTO accounts (username, password, email, role_id) VALUES (%s, %s, %s, %s)', (username, hashed_pass, email, role_id))
                mysql.connection.commit()
                return jsonify({'message': 'Đăng ký thành công'}), 201
    except Exception as e:
        print(f"Lỗi đăng ký: {e}")
        return jsonify({'message': f'Đã có lỗi xảy ra: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')  # Sử dụng email
        password = data.get('password')

        if not email or not password:
            return jsonify({'message': 'Vui lòng điền đầy đủ thông tin'}), 400
        
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))  # Sử dụng email
            account = cursor.fetchone()

            if account and verify_password(password, account['password']):
                # Đăng nhập thành công
                session['loggedin'] = True
                session['id'] = account['id']
                session['email'] = account['email']  # Sử dụng email
                session['role_id'] = account['role_id']
                return jsonify({'message': 'Đăng nhập thành công', 'role_id': account['role_id']}), 200
            else:
                # Sai email hoặc mật khẩu
                return jsonify({'message': 'Sai email hoặc mật khẩu'}), 401
            
            

    except Exception as e:
        print(f"Lỗi đăng nhập: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# === API endpoints cho forgot_password ===

@app.route('/api/forgot_password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'message': 'Vui lòng nhập địa chỉ email'}), 400

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account:
            verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) # Tạo mã xác thực ngẫu nhiên
            session['verification_code'] = verification_code # Lưu mã xác thực vào session
            session['email_to_reset'] = email # Lưu email vào session

            send_verification_email(email, verification_code) # Gửi email xác thực

            return jsonify({'message': 'Mã xác thực đã được gửi đến email của bạn'}), 200
        else:
            return jsonify({'message': 'Email không tồn tại'}), 404

    except Exception as e:
        print(f"Lỗi gửi mã xác thực: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/change_password', methods=['POST'])
def change_password():
    try:
        data = request.get_json()
        email = data.get('email')
        verification_code = data.get('verificationCode')
        new_password = data.get('newPassword')

        if not email or not verification_code or not new_password:
            return jsonify({'message': 'Vui lòng điền đầy đủ thông tin'}), 400

        if verification_code != session.get('verification_code') or email != session.get('email_to_reset'):
            return jsonify({'message': 'Mã xác thực không đúng'}), 400

        hashed_pass = hash_password(new_password)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE accounts SET password = %s WHERE email = %s', (hashed_pass, email))
        mysql.connection.commit()

        return jsonify({'message': 'Đổi mật khẩu thành công'}), 200

    except Exception as e:
        print(f"Lỗi đổi mật khẩu: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500


# === API endpoints cho pet ===

@app.route('/api/pets', methods=['POST'])
@login_required
def add_pet():
    # Lấy dữ liệu từ form
    pet_name = request.form.get('pet_name')
    pet_type = request.form.get('pet_type')
    pet_age = request.form.get('pet_age')
    pet_birthday = request.form.get('pet_birthday')
    pet_gender = request.form.get('pet_gender')
    pet_color = request.form.get('pet_color')
    pet_image = request.files.get('pet_image')

    # Kiểm tra dữ liệu đầu vào
    if not pet_name or not pet_type or not pet_image:
        return jsonify({'message': 'Vui lòng điền đầy đủ thông tin'}), 400
    if not allowed_file(pet_image.filename):
        return jsonify({'message': 'Định dạng ảnh không được phép'}), 400

    # Lưu ảnh vào thư mục uploads
    UPLOAD_PATH = os.path.abspath('../frontend/public/uploads')
    filename = pet_image.filename
    pet_image.save(os.path.join(UPLOAD_PATH, filename))

    # Thêm thú cưng vào database
    user_id = session['id']
    try:
        with mysql.connection.cursor() as cursor:
            cursor.execute('INSERT INTO pets (user_id, pet_name, pet_type, pet_age, pet_birthday, pet_gender, pet_color, pet_image) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                            (user_id, pet_name, pet_type, pet_age, pet_birthday, pet_gender, pet_color, filename))
            mysql.connection.commit()
        return jsonify({'message': 'Thêm thú cưng thành công'}), 201
    except Exception as e:
        print(f"Lỗi thêm thú cưng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500
    
@app.route('/api/pets', methods=['GET'])
@login_required
def get_pets():
    user_id = session['id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM pets WHERE user_id = %s', (user_id,))
    pets = cursor.fetchall()
    return jsonify(pets)

@app.route('/api/pets/<int:pet_id>', methods=['DELETE'])
@login_required
def delete_pet(pet_id):
    try:
        with mysql.connection.cursor() as cursor:
            # Xóa thú cưng khỏi database
            cursor.execute('DELETE FROM pets WHERE id = %s AND user_id = %s', (pet_id, session['id']))
            mysql.connection.commit()
        return jsonify({'message': 'Xóa thú cưng thành công'}), 200
    except Exception as e:
        print(f"Lỗi xóa thú cưng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/pets/<int:pet_id>', methods=['PATCH'])
@login_required
def update_pet(pet_id):
    try:
        data = request.get_json()
        pet_name = data.get('pet_name')
        pet_type = data.get('pet_type')
        pet_age = data.get('pet_age')
        pet_birthday = data.get('pet_birthday')
        pet_gender = data.get('pet_gender')
        pet_color = data.get('pet_color')

        with mysql.connection.cursor() as cursor:
            # Cập nhật thông tin thú cưng trong database
            query = "UPDATE pets SET pet_name = %s, pet_type = %s, pet_age = %s, pet_birthday = %s, pet_gender = %s, pet_color = %s WHERE id = %s AND user_id = %s"
            values = (pet_name, pet_type, pet_age, pet_birthday, pet_gender, pet_color, pet_id, session['id'])
            cursor.execute(query, values)
            mysql.connection.commit()
        return jsonify({'message': 'Cập nhật thú cưng thành công'}), 200
    except Exception as e:
        print(f"Lỗi cập nhật thú cưng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/pets/<int:pet_id>', methods=['GET'])
@login_required
def get_pet_details(pet_id):
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # Lấy thông tin thú cưng
            cursor.execute('SELECT * FROM pets WHERE id = %s AND user_id = %s', (pet_id, session['id']))
            pet = cursor.fetchone()

            if not pet:
                return jsonify({'message': 'Không tìm thấy thú cưng'}), 404

            # Lấy thông tin cân nặng
            cursor.execute('SELECT * FROM pet_weight WHERE pet_id = %s', (pet_id,))
            pet['weights'] = cursor.fetchall()

            # Lấy thông tin vắc xin
            cursor.execute('SELECT * FROM pet_vaccines WHERE pet_id = %s', (pet_id,))
            pet['vaccines'] = cursor.fetchall()

            # Lấy thông tin thuốc
            cursor.execute('SELECT * FROM pet_medications WHERE pet_id = %s', (pet_id,))
            pet['medications'] = cursor.fetchall()

            # Lấy thông tin dị ứng
            cursor.execute('SELECT * FROM pet_allergies WHERE pet_id = %s', (pet_id,))
            pet['allergies'] = cursor.fetchall()

        return jsonify(pet)
    except Exception as e:
        print(f"Lỗi lấy thông tin chi tiết thú cưng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/pets/<int:pet_id>/weight', methods=['POST'])
@login_required
def add_pet_weight(pet_id):
    try:
        weight = request.form.get('weight')
        date_recorded = request.form.get('date_recorded')

        if not weight or not date_recorded:
            return jsonify({'message': 'Vui lòng điền đầy đủ thông tin'}), 400

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('INSERT INTO pet_weight (pet_id, user_id, weight, date_recorded) VALUES (%s, %s, %s, %s)',
                           (pet_id, session['id'], weight, date_recorded))
            mysql.connection.commit()

            # Lấy thông tin pet đã cập nhật
            cursor.execute('SELECT * FROM pets WHERE id = %s AND user_id = %s', (pet_id, session['id']))
            pet = cursor.fetchone()

            # Lấy thông tin cân nặng
            cursor.execute('SELECT * FROM pet_weight WHERE pet_id = %s', (pet_id,))
            pet['weights'] = cursor.fetchall()

        return jsonify(pet), 201
    except Exception as e:
        print(f"Lỗi thêm cân nặng cho thú cưng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/pets/<int:pet_id>/weight/<int:weight_id>', methods=['DELETE'])
@login_required
def delete_pet_weight(pet_id, weight_id):
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # Xóa bản ghi cân nặng
            cursor.execute('DELETE FROM pet_weight WHERE id = %s AND pet_id = %s AND user_id = %s', (weight_id, pet_id, session['id']))
            mysql.connection.commit()

            # Lấy thông tin pet đã cập nhật
            cursor.execute('SELECT * FROM pets WHERE id = %s AND user_id = %s', (pet_id, session['id']))
            pet = cursor.fetchone()

            # Lấy thông tin cân nặng
            cursor.execute('SELECT * FROM pet_weight WHERE pet_id = %s', (pet_id,))
            pet['weights'] = cursor.fetchall()

        return jsonify(pet), 200
    except Exception as e:
        print(f"Lỗi xóa cân nặng cho thú cưng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500
    
@app.route('/api/pets/<int:pet_id>/vaccines', methods=['POST'])
@login_required
def add_pet_vaccine(pet_id):
    try:
        vaccine_name = request.form.get('vaccine_name')
        dosage = request.form.get('dosage')
        date_administered = request.form.get('date_administered')

        if not vaccine_name or not dosage or not date_administered:
            return jsonify({'message': 'Vui lòng điền đầy đủ thông tin'}), 400

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('INSERT INTO pet_vaccines (pet_id, user_id, vaccine_name, dosage, date_administered) VALUES (%s, %s, %s, %s, %s)',
                           (pet_id, session['id'], vaccine_name, dosage, date_administered))
            mysql.connection.commit()

            # Lấy lại thông tin thú cưng (bao gồm cả vắc xin mới)
            cursor.execute('SELECT * FROM pets WHERE id = %s AND user_id = %s', (pet_id, session['id']))
            pet = cursor.fetchone()
            if not pet:
                return jsonify({'message': 'Không tìm thấy thú cưng'}), 404
            cursor.execute('SELECT * FROM pet_vaccines WHERE pet_id = %s', (pet_id,))
            pet['vaccines'] = cursor.fetchall()

        return jsonify(pet), 201
    except Exception as e:
        print(f"Lỗi thêm vắc xin: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/pets/<int:pet_id>/vaccines/<int:vaccine_id>', methods=['DELETE'])
@login_required
def delete_pet_vaccine(pet_id, vaccine_id):
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('DELETE FROM pet_vaccines WHERE id = %s AND pet_id = %s AND user_id = %s', (vaccine_id, pet_id, session['id']))
            mysql.connection.commit()

            # Lấy lại thông tin thú cưng (bao gồm cả danh sách vắc xin đã cập nhật)
            cursor.execute('SELECT * FROM pets WHERE id = %s AND user_id = %s', (pet_id, session['id']))
            pet = cursor.fetchone()
            if not pet:
                return jsonify({'message': 'Không tìm thấy thú cưng'}), 404
            cursor.execute('SELECT * FROM pet_vaccines WHERE pet_id = %s', (pet_id,))
            pet['vaccines'] = cursor.fetchall()

        return jsonify(pet), 200
    except Exception as e:
        print(f"Lỗi xóa vắc xin: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500
    
@app.route('/api/pets/<int:pet_id>/medications', methods=['POST'])
@login_required
def add_pet_medication(pet_id):
    try:
        medication_name = request.form.get('medication_name')
        dosage = request.form.get('dosage')
        date_administered = request.form.get('date_administered')

        if not medication_name or not dosage or not date_administered:
            return jsonify({'message': 'Vui lòng điền đầy đủ thông tin'}), 400

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('INSERT INTO pet_medications (pet_id, user_id, medication_name, dosage, date_administered) VALUES (%s, %s, %s, %s, %s)',
                           (pet_id, session['id'], medication_name, dosage, date_administered))
            mysql.connection.commit()

            # Lấy lại thông tin thú cưng (bao gồm cả thuốc mới)
            cursor.execute('SELECT * FROM pets WHERE id = %s AND user_id = %s', (pet_id, session['id']))
            pet = cursor.fetchone()
            if not pet:
                return jsonify({'message': 'Không tìm thấy thú cưng'}), 404
            cursor.execute('SELECT * FROM pet_medications WHERE pet_id = %s', (pet_id,))
            pet['medications'] = cursor.fetchall()

        return jsonify(pet), 201
    except Exception as e:
        print(f"Lỗi thêm thuốc: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/pets/<int:pet_id>/medications/<int:medication_id>', methods=['DELETE'])
@login_required
def delete_pet_medication(pet_id, medication_id):
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('DELETE FROM pet_medications WHERE id = %s AND pet_id = %s AND user_id = %s', (medication_id, pet_id, session['id']))
            mysql.connection.commit()

            # Lấy lại thông tin thú cưng (bao gồm cả danh sách thuốc đã cập nhật)
            cursor.execute('SELECT * FROM pets WHERE id = %s AND user_id = %s', (pet_id, session['id']))
            pet = cursor.fetchone()
            if not pet:
                return jsonify({'message': 'Không tìm thấy thú cưng'}), 404
            cursor.execute('SELECT * FROM pet_medications WHERE pet_id = %s', (pet_id,))
            pet['medications'] = cursor.fetchall()

        return jsonify(pet), 200
    except Exception as e:
        print(f"Lỗi xóa thuốc: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500
    
@app.route('/api/pets/<int:pet_id>/allergies', methods=['POST'])
@login_required
def add_pet_allergy(pet_id):
    try:
        allergy = request.form.get('allergy')
        cause = request.form.get('cause')
        symptoms = request.form.get('symptoms')

        if not allergy or not cause or not symptoms:
            return jsonify({'message': 'Vui lòng điền đầy đủ thông tin'}), 400

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('INSERT INTO pet_allergies (pet_id, user_id, allergy, cause, symptoms) VALUES (%s, %s, %s, %s, %s)',
                           (pet_id, session['id'], allergy, cause, symptoms))
            mysql.connection.commit()

            # Lấy lại thông tin thú cưng (bao gồm cả dị ứng mới)
            cursor.execute('SELECT * FROM pets WHERE id = %s AND user_id = %s', (pet_id, session['id']))
            pet = cursor.fetchone()
            if not pet:
                return jsonify({'message': 'Không tìm thấy thú cưng'}), 404
            cursor.execute('SELECT * FROM pet_allergies WHERE pet_id = %s', (pet_id,))
            pet['allergies'] = cursor.fetchall()

        return jsonify(pet), 201
    except Exception as e:
        print(f"Lỗi thêm dị ứng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/pets/<int:pet_id>/allergies/<int:allergy_id>', methods=['DELETE'])
@login_required
def delete_pet_allergy(pet_id, allergy_id):
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('DELETE FROM pet_allergies WHERE id = %s AND pet_id = %s AND user_id = %s', (allergy_id, pet_id, session['id']))
            mysql.connection.commit()

            # Lấy lại thông tin thú cưng (bao gồm cả danh sách dị ứng đã cập nhật)
            cursor.execute('SELECT * FROM pets WHERE id = %s AND user_id = %s', (pet_id, session['id']))
            pet = cursor.fetchone()
            if not pet:
                return jsonify({'message': 'Không tìm thấy thú cưng'}), 404
            cursor.execute('SELECT * FROM pet_allergies WHERE pet_id = %s', (pet_id,))
            pet['allergies'] = cursor.fetchall()

        return jsonify(pet), 200
    except Exception as e:
        print(f"Lỗi xóa dị ứng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500


# === API endpoints cho veterinarian contacts ===

@app.route('/api/veterinarian_contacts', methods=['POST'])
@login_required
def add_veterinarian_contact():
    try:
        data = request.get_json()
        contact_name = data.get('contact_name')
        contact_gender = data.get('contact_gender')
        contact_language = data.get('contact_language')
        contact_phone = data.get('contact_phone')
        vet_address = data.get('vet_address')
        vet_email = data.get('vet_email')
        vet_speciality = data.get('vet_speciality')
        vet_clinic = data.get('vet_clinic')

        # Validate dữ liệu đầu vào (nếu cần)

        with mysql.connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO veterinarian_contacts (user_id, contact_name, contact_gender, contact_language, contact_phone, vet_address, vet_email, vet_speciality, vet_clinic) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (session['id'], contact_name, contact_gender, contact_language, contact_phone, vet_address, vet_email, vet_speciality, vet_clinic)
            )
            mysql.connection.commit()

        return jsonify({'message': 'Thêm liên lạc bác sĩ thú y thành công'}), 201
    except Exception as e:
        print(f"Lỗi thêm liên lạc bác sĩ thú y: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500
    
@app.route('/api/veterinarian_contacts', methods=['GET'])
@login_required
def get_veterinarian_contacts():
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM veterinarian_contacts WHERE user_id = %s', (session['id'],))
            contacts = cursor.fetchall()
        return jsonify(contacts)
    except Exception as e:
        print(f"Lỗi lấy danh sách liên lạc bác sĩ thú y: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500
    
@app.route('/api/veterinarian_contacts/<int:contact_id>', methods=['PUT'])
@login_required
def update_veterinarian_contact(contact_id):
    try:
        data = request.get_json()
        contact_name = data.get('contact_name')
        contact_gender = data.get('contact_gender')
        contact_language = data.get('contact_language')
        contact_phone = data.get('contact_phone')
        vet_address = data.get('vet_address')
        vet_email = data.get('vet_email')
        vet_speciality = data.get('vet_speciality')
        vet_clinic = data.get('vet_clinic')

        # Validate dữ liệu đầu vào (nếu cần)
        # ...

        with mysql.connection.cursor() as cursor:
            # Cập nhật thông tin liên lạc trong database
            cursor.execute(
                """
                UPDATE veterinarian_contacts 
                SET 
                    contact_name = %s, 
                    contact_gender = %s, 
                    contact_language = %s, 
                    contact_phone = %s, 
                    vet_address = %s, 
                    vet_email = %s, 
                    vet_speciality = %s, 
                    vet_clinic = %s 
                WHERE id = %s AND user_id = %s
                """,
                (contact_name, contact_gender, contact_language, contact_phone, vet_address, vet_email, vet_speciality, vet_clinic, contact_id, session['id'])
            )
            mysql.connection.commit()

        return jsonify({'message': 'Cập nhật liên lạc bác sĩ thú y thành công'}), 200
    except Exception as e:
        print(f"Lỗi cập nhật liên lạc bác sĩ thú y: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500
    
@app.route('/api/veterinarian_contacts/<int:contact_id>', methods=['DELETE'])
@login_required
def delete_veterinarian_contact(contact_id):
    try:
        with mysql.connection.cursor() as cursor:
            cursor.execute('DELETE FROM veterinarian_contacts WHERE id = %s AND user_id = %s', (contact_id, session['id']))
            mysql.connection.commit()

        return jsonify({'message': 'Xóa liên lạc bác sĩ thú y thành công'}), 200
    except Exception as e:
        print(f"Lỗi xóa liên lạc bác sĩ thú y: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500


# === API endpoints cho products ===

@app.route('/api/products', methods=['GET'])
@login_required
def get_products():
    # Lấy danh sách tất cả sản phẩm (cho user)
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT p.*, c.username AS customer_name FROM products p JOIN accounts c ON p.customer_id = c.id') # Lấy thêm tên customer
            products = cursor.fetchall()

            for product in products:
                # Lấy danh sách hình ảnh của sản phẩm
                cursor.execute('SELECT image_url FROM product_images WHERE product_id = %s', (product['id'],))
                # Trả về mảng các chuỗi đường dẫn hình ảnh
                product['images'] = [row['image_url'] for row in cursor.fetchall()]
                product['price'] = format_currency(product['price'])
        return jsonify(products)
    except Exception as e:
        print(f"Lỗi lấy danh sách sản phẩm: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500
    
@app.route('/api/admin/products', methods=['GET'])  # Đổi tên endpoint để phân biệt
@login_required
def get_all_products():
    try:
        # Kiểm tra role (chỉ admin mới được phép truy cập)
        if session['role_id'] != 2:
            return jsonify({'message': 'Bạn không có quyền truy cập'}), 403

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # Sử dụng JOIN để lấy thêm tên customer
            cursor.execute("""
                SELECT p.*, a.username AS customer_name 
                FROM products p
                JOIN accounts a ON p.customer_id = a.id
            """)
            products = cursor.fetchall()

            for product in products:
                # Lấy danh sách hình ảnh của sản phẩm
                cursor.execute('SELECT image_url FROM product_images WHERE product_id = %s', (product['id'],))
                product['images'] = [row['image_url'] for row in cursor.fetchall()]
                product['price'] = format_currency(product['price'])

        return jsonify(products)
    except Exception as e:
        print(f"Lỗi lấy danh sách sản phẩm: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500
    
@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
@login_required
def update_product_admin(product_id):
    try:
        # Kiểm tra role (chỉ admin mới được phép truy cập)
        if session['role_id'] != 2:
            return jsonify({'message': 'Bạn không có quyền truy cập'}), 403

        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        images = request.files.getlist('images[]')
        quantity = request.form.get('quantity')

        # Validate dữ liệu đầu vào (nếu cần)
        # ...

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # Cập nhật thông tin sản phẩm trong database
            update_fields = []
            update_values = []
            if name:
                update_fields.append('name = %s')
                update_values.append(name)
            if description:
                update_fields.append('description = %s')
                update_values.append(description)
            if price:
                update_fields.append('price = %s')
                update_values.append(price)
            if quantity:
                update_fields.append('quantity = %s')
                update_values.append(quantity)

            if update_fields:
                query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = %s"
                update_values.append(product_id)
                cursor.execute(query, tuple(update_values))

            # Xử lý hình ảnh (nếu có)
            if images:
                # Xóa hình ảnh cũ (nếu có)
                cursor.execute('DELETE FROM product_images WHERE product_id = %s', (product_id,))

                UPLOAD_PATH = os.path.abspath('../frontend/public/uploads')
                filenames = []
                for image in images:
                    if not allowed_file(image.filename):
                        return jsonify({'message': 'Định dạng ảnh không được phép'}), 400
                    filename = image.filename
                    image.save(os.path.join(UPLOAD_PATH, filename))
                    filenames.append(filename)

                # Thêm hình ảnh mới
                if filenames:
                    for i, filename in enumerate(filenames):
                        is_main = i == 0  # Hình ảnh đầu tiên là hình ảnh chính
                        cursor.execute('INSERT INTO product_images (product_id, image_url, is_main) VALUES (%s, %s, %s)', (product_id, filename, is_main))

            mysql.connection.commit()

        return jsonify({'message': 'Cập nhật sản phẩm thành công'}), 200
    except Exception as e:
        print(f"Lỗi cập nhật sản phẩm: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500
    
@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product_admin(product_id):
    try:
        # Kiểm tra role (chỉ admin mới được phép truy cập)
        if session['role_id'] != 2:
            return jsonify({'message': 'Bạn không có quyền truy cập'}), 403

        with mysql.connection.cursor() as cursor:
            # Xóa sản phẩm khỏi database
            cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
            mysql.connection.commit()

        return jsonify({'message': 'Xóa sản phẩm thành công'}), 200
    except Exception as e:
        print(f"Lỗi xóa sản phẩm: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/products/<int:product_id>', methods=['GET'])
@login_required
def get_product(product_id):
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # Lấy thông tin sản phẩm
            cursor.execute('SELECT p.*, c.username AS customer_name, c.email AS customer_email FROM products p JOIN accounts c ON p.customer_id = c.id WHERE p.id = %s', (product_id,))
            product = cursor.fetchone()
            if not product:
                return jsonify({'message': 'Không tìm thấy sản phẩm'}), 404

            # Tăng lượt xem
            cursor.execute('UPDATE products SET views = views + 1 WHERE id = %s', (product_id,))
            mysql.connection.commit()

            # Lấy danh sách hình ảnh của sản phẩm
            cursor.execute('SELECT image_url, is_main FROM product_images WHERE product_id = %s', (product_id,))
            product['images'] = cursor.fetchall()
            product['price'] = format_currency(product['price'])

        return jsonify(product)
    except Exception as e:
        print(f"Lỗi lấy thông tin sản phẩm: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/products/my', methods=['GET'])
@login_required
def get_my_products():
    # Lấy danh sách sản phẩm của customer hiện tại
    try:
        if session['role_id'] != 3:  # Chỉ customer mới được phép truy cập
            return jsonify({'message': 'Bạn không có quyền truy cập'}), 403

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM products WHERE customer_id = %s', (session['id'],))
            products = cursor.fetchall()

            for product in products:
            # Lấy danh sách hình ảnh của sản phẩm
                cursor.execute('SELECT image_url FROM product_images WHERE product_id = %s', (product['id'],))
                # Trả về mảng các chuỗi đường dẫn hình ảnh
                product['images'] = [row['image_url'] for row in cursor.fetchall()] 
                product['price'] = format_currency(product['price'])

        return jsonify(products)
    except Exception as e:
        print(f"Lỗi lấy danh sách sản phẩm của customer: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/products', methods=['POST'])
@login_required
def add_product():
    try:
        if session['role_id'] not in (2, 3):  # Chỉ customer và admin mới được phép thêm sản phẩm
            return jsonify({'message': 'Bạn không có quyền thêm sản phẩm'}), 403

        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        images = request.files.getlist('images[]')
        quantity = request.form.get('quantity')

        if not name or not description or not price or not images or not quantity:
            return jsonify({'message': 'Vui lòng điền đầy đủ thông tin'}), 400

        # Lưu các hình ảnh vào thư mục uploads
        UPLOAD_PATH = os.path.abspath('../frontend/public/uploads')
        filenames = []
        for image in images:
            if not allowed_file(image.filename):
                return jsonify({'message': 'Định dạng ảnh không được phép'}), 400
            filename = image.filename
            image.save(os.path.join(UPLOAD_PATH, filename))
            filenames.append(filename)

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('INSERT INTO products (customer_id, name, description, price, quantity) VALUES (%s, %s, %s, %s, %s)',
                           (session['id'], name, description, price, quantity))
            product_id = cursor.lastrowid

            # Thêm thông tin hình ảnh vào bảng product_images
            if filenames:
                for i, filename in enumerate(filenames):
                    is_main = i == 0  # Hình ảnh đầu tiên là hình ảnh chính
                    cursor.execute('INSERT INTO product_images (product_id, image_url, is_main) VALUES (%s, %s, %s)', (product_id, filename, is_main))

            mysql.connection.commit()
        return jsonify({'message': 'Thêm sản phẩm thành công'}), 201
    except Exception as e:
        print(f"Lỗi thêm sản phẩm: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/products/<int:product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    # Cập nhật thông tin sản phẩm (cho customer và admin)
    try:
        # 1. Kiểm tra phân quyền: Chỉ customer và admin mới được phép sửa sản phẩm
        if session['role_id'] not in (2, 3):  
            return jsonify({'message': 'Bạn không có quyền sửa sản phẩm'}), 403

        # 2. Lấy dữ liệu từ request
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        images = request.files.getlist('images[]') # Lấy danh sách hình ảnh
        quantity = request.form.get('quantity')

        # 3. Kiểm tra dữ liệu đầu vào
        if not name or not description or not price or not quantity:
            return jsonify({'message': 'Vui lòng điền đầy đủ thông tin'}), 400

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # 4. Kiểm tra quyền sở hữu sản phẩm: Chỉ cho phép sửa sản phẩm của chính mình hoặc nếu là admin
            cursor.execute('SELECT customer_id FROM products WHERE id = %s', (product_id,))
            product = cursor.fetchone()
            if not product or (product['customer_id'] != session['id'] and session['role_id'] != 2):
                return jsonify({'message': 'Bạn không có quyền sửa sản phẩm này'}), 403

            # 5. Cập nhật thông tin sản phẩm trong database
            update_fields = []
            update_values = []
            if name:
                update_fields.append('name = %s')
                update_values.append(name)
            if description:
                update_fields.append('description = %s')
                update_values.append(description)
            if price:
                update_fields.append('price = %s')
                update_values.append(price)
            if quantity:
                update_fields.append('quantity = %s')
                update_values.append(quantity)

            if update_fields:
                query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = %s"
                update_values.append(product_id)
                cursor.execute(query, tuple(update_values))

            # 6. Xử lý hình ảnh: Xóa hình ảnh cũ (nếu có) và thêm hình ảnh mới
            if images:
                cursor.execute('DELETE FROM product_images WHERE product_id = %s', (product_id,))
                UPLOAD_PATH = os.path.abspath('../frontend/public/uploads')
                filenames = []
                for image in images:
                    if not allowed_file(image.filename):
                        return jsonify({'message': 'Định dạng ảnh không được phép'}), 400
                    filename = image.filename
                    image.save(os.path.join(UPLOAD_PATH, filename))
                    filenames.append(filename)
                
                if filenames:
                    for i, filename in enumerate(filenames):
                        is_main = i == 0  # Hình ảnh đầu tiên là hình ảnh chính
                        cursor.execute('INSERT INTO product_images (product_id, image_url, is_main) VALUES (%s, %s, %s)', (product_id, filename, is_main))

            mysql.connection.commit()

        return jsonify({'message': 'Cập nhật sản phẩm thành công'}), 200
    except Exception as e:
        print(f"Lỗi cập nhật sản phẩm: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    # Xóa sản phẩm (cho customer và admin)
    try:
        # 1. Kiểm tra phân quyền: Chỉ customer và admin mới được phép xóa sản phẩm
        if session['role_id'] not in (2, 3):  
            return jsonify({'message': 'Bạn không có quyền xóa sản phẩm'}), 403

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # 2. Kiểm tra quyền sở hữu sản phẩm: Chỉ cho phép xóa sản phẩm của chính mình hoặc nếu là admin
            cursor.execute('SELECT customer_id FROM products WHERE id = %s', (product_id,))
            product = cursor.fetchone()
            if not product or (product['customer_id'] != session['id'] and session['role_id'] != 2):
                return jsonify({'message': 'Bạn không có quyền xóa sản phẩm này'}), 403

            # Xóa sản phẩm khỏi giỏ hàng
            cursor.execute('DELETE FROM cart WHERE product_id = %s', (product_id,))

            # 3. Xóa sản phẩm trong database
            cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
            mysql.connection.commit()

        return jsonify({'message': 'Xóa sản phẩm thành công'}), 200
    except Exception as e:
        print(f"Lỗi xóa sản phẩm: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500


# === API endpoints cho service ===

@app.route('/api/services/my', methods=['GET'])
@login_required
def get_my_services():
    """Lấy danh sách dịch vụ của customer hiện tại."""
    try:
        if session['role_id'] != 3:  # Chỉ customer mới được phép truy cập
            return jsonify({'message': 'Bạn không có quyền truy cập'}), 403

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM services WHERE customer_id = %s', (session['id'],))
            services = cursor.fetchall()

            for service in services:
                service['price'] = format_currency(service['price'])

        return jsonify(services)
    except Exception as e:
        print(f"Lỗi lấy danh sách dịch vụ của customer: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/services', methods=['POST'])
@login_required
def add_service():
    """Thêm dịch vụ mới."""
    try:
        if session['role_id'] not in (2, 3):  # Chỉ customer và admin mới được phép thêm dịch vụ
            return jsonify({'message': 'Bạn không có quyền thêm dịch vụ'}), 403

        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        price = data.get('price')

        # Validate dữ liệu đầu vào (nếu cần)
        # ...

        with mysql.connection.cursor() as cursor:
            cursor.execute(
                'INSERT INTO services (customer_id, name, description, price) VALUES (%s, %s, %s, %s)',
                (session['id'], name, description, price)
            )
            mysql.connection.commit()

        return jsonify({'message': 'Thêm dịch vụ thành công'}), 201
    except Exception as e:
        print(f"Lỗi thêm dịch vụ: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/services/<int:service_id>', methods=['PUT'])
@login_required
def update_service(service_id):
    """Cập nhật thông tin dịch vụ."""
    try:
        if session['role_id'] not in (2, 3):  # Chỉ customer và admin mới được phép sửa dịch vụ
            return jsonify({'message': 'Bạn không có quyền sửa dịch vụ'}), 403

        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        price = data.get('price')

        # Validate dữ liệu đầu vào (nếu cần)
        # ...

        with mysql.connection.cursor() as cursor:
            # Cập nhật thông tin dịch vụ trong database
            update_fields = []
            update_values = []
            if name:
                update_fields.append('name = %s')
                update_values.append(name)
            if description:
                update_fields.append('description = %s')
                update_values.append(description)
            if price:
                update_fields.append('price = %s')
                update_values.append(price)

            if update_fields:
                query = f"UPDATE services SET {', '.join(update_fields)} WHERE id = %s AND customer_id = %s"
                update_values.extend([service_id, session['id']])
                cursor.execute(query, tuple(update_values))

            mysql.connection.commit()

        return jsonify({'message': 'Cập nhật dịch vụ thành công'}), 200
    except Exception as e:
        print(f"Lỗi cập nhật dịch vụ: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@login_required
def delete_service(service_id):
    """Xóa dịch vụ."""
    try:
        if session['role_id'] not in (2, 3):  # Chỉ customer và admin mới được phép xóa dịch vụ
            return jsonify({'message': 'Bạn không có quyền xóa dịch vụ'}), 403

        with mysql.connection.cursor() as cursor:
            # Xóa dịch vụ khỏi database
            cursor.execute('DELETE FROM services WHERE id = %s AND customer_id = %s', (service_id, session['id']))
            mysql.connection.commit()

        return jsonify({'message': 'Xóa dịch vụ thành công'}), 200
    except Exception as e:
        print(f"Lỗi xóa dịch vụ: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/services', methods=['GET'])
def get_services():
    """Lấy danh sách tất cả dịch vụ."""
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM services')
            services = cursor.fetchall()

            for service in services:
                service['price'] = format_currency(service['price'])

        return jsonify(services)
    except Exception as e:
        print(f"Lỗi lấy danh sách dịch vụ: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500


# === API endpoints cho cart ===

@app.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT c.id AS cart_item_id, c.quantity, p.*  FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id = %s', (session['id'],))
            cart_items = cursor.fetchall()
            for item in cart_items:
                cursor.execute('SELECT image_url FROM product_images WHERE product_id = %s', (item['id'],))
                item['images'] = [row['image_url'] for row in cursor.fetchall()]
        return jsonify(cart_items), 200
    except Exception as e:
        print(f"Lỗi lấy giỏ hàng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        if not product_id:
            return jsonify({'message': 'Vui lòng cung cấp product_id'}), 400

        # Kiểm tra số lượng sản phẩm
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT quantity FROM products WHERE id = %s', (product_id,))
            product = cursor.fetchone()
            if not product:
                return jsonify({'message': 'Không tìm thấy sản phẩm'}), 404
            if product['quantity'] < quantity:
                return jsonify({'message': 'Số lượng sản phẩm không đủ'}), 400

        # Thêm sản phẩm vào bảng cart
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # Kiểm tra xem sản phẩm đã có trong giỏ hàng chưa
            cursor.execute('SELECT * FROM cart WHERE user_id = %s AND product_id = %s', (session['id'], product_id))
            existing_item = cursor.fetchone()

            if existing_item:
                # Nếu đã có, cập nhật số lượng
                new_quantity = existing_item['quantity'] + quantity
                cursor.execute('UPDATE cart SET quantity = %s WHERE id = %s', (new_quantity, existing_item['id']))
            else:
                # Nếu chưa có, thêm mới
                cursor.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)', (session['id'], product_id, quantity))
            mysql.connection.commit()

        # Lấy giỏ hàng mới từ bảng cart
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT c.id AS cart_item_id, c.quantity, p.*  FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id = %s', (session['id'],))
            cart_items = cursor.fetchall()
            for item in cart_items:
                cursor.execute('SELECT image_url FROM product_images WHERE product_id = %s', (item['id'],))
                item['images'] = [row['image_url'] for row in cursor.fetchall()]

        return jsonify({'message': 'Thêm sản phẩm vào giỏ hàng thành công', 'cart': cart_items}), 200 # Trả về giỏ hàng mới
    except Exception as e:
        print(f"Lỗi thêm sản phẩm vào giỏ hàng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/cart/remove/<int:cart_item_id>', methods=['DELETE']) 
@login_required
def remove_from_cart(cart_item_id):
    try:
        # Xóa sản phẩm khỏi bảng cart
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('DELETE FROM cart WHERE id = %s AND user_id = %s', (cart_item_id, session['id'])) # Sử dụng cart_item_id để xóa
            mysql.connection.commit()

        return jsonify({'message': 'Xóa sản phẩm khỏi giỏ hàng thành công'}), 200
    except Exception as e:
        print(f"Lỗi xóa sản phẩm khỏi giỏ hàng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/cart/update', methods=['PUT'])
@login_required
def update_cart():
    try:
        data = request.get_json()
        cart_item_id = data.get('cart_item_id') # Sử dụng cart_item_id
        quantity = data.get('quantity')

        if not cart_item_id or not quantity:
            return jsonify({'message': 'Vui lòng cung cấp cart_item_id và quantity'}), 400

        # Kiểm tra số lượng sản phẩm
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('SELECT p.quantity FROM products p JOIN cart c ON p.id = c.product_id WHERE c.id = %s', (cart_item_id,))
            product = cursor.fetchone()
            if not product:
                return jsonify({'message': 'Không tìm thấy sản phẩm'}), 404
            if product['quantity'] < quantity:
                return jsonify({'message': 'Số lượng sản phẩm không đủ'}), 400

        # Cập nhật số lượng trong bảng cart
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute('UPDATE cart SET quantity = %s WHERE user_id = %s AND id = %s', (quantity, session['id'], cart_item_id))
            mysql.connection.commit()

        return jsonify({'message': 'Cập nhật giỏ hàng thành công'}), 200
    except Exception as e:
        print(f"Lỗi cập nhật giỏ hàng: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/cart/checkout', methods=['POST'])
@login_required
def checkout():
    print("session:", session)
    try:
        data = request.get_json()
        recipient_info = data.get('recipient_info', {})
        shipping_address = data.get('shipping_address', {})
        notes = data.get('notes', '')

        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            try:
                # Bắt đầu transaction
                cursor.execute('START TRANSACTION')

                # Lấy thông tin giỏ hàng từ bảng cart của user hiện tại
                cursor.execute('SELECT * FROM cart WHERE user_id = %s', (session['id'],))
                cart_items = cursor.fetchall()

                if not cart_items:
                    raise Exception('Giỏ hàng trống.')

                # Tính toán tổng tiền và kiểm tra số lượng sản phẩm
                total_amount = 0
                for item in cart_items:
                    cursor.execute('SELECT id, name, price, quantity, customer_id FROM products WHERE id = %s', (item['product_id'],))
                    product = cursor.fetchone()
                    if not product:
                        raise Exception(f'Không tìm thấy sản phẩm có id {item["product_id"]}')
                    if product['quantity'] < item['quantity']:
                        raise Exception(f'Số lượng sản phẩm {product["name"]} không đủ')
                    total_amount += product['price'] * item['quantity']

                # Cộng thêm phí ship 
                total_amount += 25000

                # Tạo đơn hàng mới với trạng thái "pending" và customer_id từ products
                cursor.execute(
                    'INSERT INTO orders (user_id,  total_amount, order_date, status, notes) '
                    'SELECT %s, %s, %s, %s, %s FROM products WHERE id = %s',
                    (session['id'], total_amount, datetime.now(), 'pending', notes, cart_items[0]['product_id'])
                )
                order_id = cursor.lastrowid

                # Lưu địa chỉ giao hàng
                cursor.execute(
                    'INSERT INTO orders_shipping_address (order_id, province, district, ward, street) '
                    'VALUES (%s, %s, %s, %s, %s)',
                    (order_id, shipping_address['province'], shipping_address['district'], shipping_address['ward'], shipping_address['street'])
                )

                # Lưu thông tin liên lạc
                cursor.execute(
                    'INSERT INTO orders_contacts (order_id, name, phone, email) '
                    'VALUES (%s, %s, %s, %s)',
                    (order_id, recipient_info['name'], recipient_info['phone'], recipient_info['email'])
                )

                # Thêm sản phẩm vào order_items
                for item in cart_items:
                    cursor.execute('SELECT price FROM products WHERE id = %s', (item['product_id'],))
                    product_price = cursor.fetchone()['price']
                    cursor.execute('INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s)',
                                   (order_id, item['product_id'], item['quantity'], product_price))

                # Xóa giỏ hàng
                cursor.execute('DELETE FROM cart WHERE user_id = %s', (session['id'],))

                # Cập nhật lượt mua
                for item in cart_items:
                    cursor.execute('UPDATE products SET sales = sales + %s WHERE id = %s', (item['quantity'], item['product_id']))

                # Cập nhật số lượng sản phẩm trong bảng products
                for item in cart_items:
                    cursor.execute('UPDATE products SET quantity = quantity - %s WHERE id = %s', (item['quantity'], item['product_id']))



                # Tạo liên kết thanh toán PayOS
                payment_data = PaymentData(
                    orderCode=order_id,
                    amount=int(total_amount),
                    description='Đơn hàng Pet Guardian',
                    cancelUrl=f"http://localhost:3000/cancel",
                    returnUrl=f"http://localhost:3000/success"
                )
                payos_payment = payos.createPaymentLink(payment_data)

                # Commit transaction
                cursor.execute('COMMIT')

                return jsonify(payos_payment.to_json()), 200

            except Exception as e:
                # Rollback transaction nếu có lỗi
                cursor.execute('ROLLBACK')
                print(f"Lỗi thanh toán: {e}")
                return jsonify({'message': str(e)}), 500

    except Exception as e:
        print(f"Lỗi thanh toán: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500


# @app.route('/api/payos/callback', methods=['POST'])
# def payos_callback():
#     try:
#         data = request.get_json()
#         print("Dữ liệu callback từ PayOS:", data)
#         order_code = data.get('orderCode')
#         status = data.get('status')

#         with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
#             try:
#                 # Bắt đầu transaction
#                 cursor.execute('START TRANSACTION')

#                 if status == 'COMPLETED':
#                     # Cập nhật trạng thái đơn hàng
#                     cursor.execute('UPDATE orders SET status = %s WHERE id = %s', ('completed', order_code))

#                     # Lấy thông tin đơn hàng
#                     cursor.execute('SELECT * FROM orders WHERE id = %s', (order_code,))
#                     order = cursor.fetchone()

#                     # Lấy danh sách sản phẩm từ order_items
#                     cursor.execute('SELECT product_id, quantity FROM order_items WHERE order_id = %s', (order_code,))
#                     order_items = cursor.fetchall()

#                     # Cập nhật số lượng sản phẩm trong kho và sales
#                     for item in order_items:
#                         cursor.execute('UPDATE products SET quantity = quantity - %s, sales = sales + %s WHERE id = %s', (item['quantity'], item['quantity'], item['product_id']))

#                     # Xóa giỏ hàng của người dùng
#                     cursor.execute('DELETE FROM cart WHERE user_id = %s', (order['user_id'],))

#                 elif status == 'CANCELLED':
#                     # Xóa đơn hàng khi hủy thanh toán
#                     cursor.execute('DELETE FROM orders WHERE id = %s AND status = "pending"', (order_code,))

#                 # Commit transaction
#                 cursor.execute('COMMIT')

#                 return jsonify({'message': 'Xử lý callback thành công'}), 200

#             except Exception as e:
#                 # Rollback transaction nếu có lỗi
#                 cursor.execute('ROLLBACK')
#                 print(f"Lỗi xử lý callback: {e}")
#                 return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

#     except Exception as e:
#         print(f"Lỗi xử lý callback: {e}")
#         return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/customers/revenue', methods=['GET'])
@login_required
def get_customer_revenue():
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # Lấy customer_id từ session
            customer_id = session.get('customer_id')
            print(f"Customer ID: {customer_id}")
            # Truy vấn SQL để tính tổng doanh thu
            cursor.execute("""
                SELECT SUM(oi.price * oi.quantity) AS total_revenue
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE o.customer_id = %s
            """, (customer_id,))
            result = cursor.fetchone()

        total_revenue = result['total_revenue'] if result['total_revenue'] else 0
        return jsonify({'total_revenue': total_revenue}), 200

    except Exception as e:
        print(f"Lỗi lấy doanh số customer: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

@app.route('/api/admin/transactions', methods=['GET'])
@login_required
def get_transactions():
    try:
        filter = request.args.get('filter', 'today')
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # Truy vấn SQL để lấy dữ liệu giao dịch theo filter
            if filter == 'today':
                cursor.execute("""
                    SELECT id, user_id, total_amount, order_date
                    FROM orders
                    WHERE DATE(order_date) = CURDATE()
                """)
            elif filter == 'yesterday':
                cursor.execute("""
                    SELECT id, user_id, total_amount, order_date
                    FROM orders
                    WHERE DATE(order_date) = CURDATE() - INTERVAL 1 DAY
                """)
            elif filter == 'this_week':
                cursor.execute("""
                    SELECT id, user_id, total_amount, order_date
                    FROM orders
                    WHERE YEARWEEK(order_date, 1) = YEARWEEK(CURDATE(), 1)
                """)
            elif filter == 'last_week':
                cursor.execute("""
                    SELECT id, user_id, total_amount, order_date
                    FROM orders
                    WHERE YEARWEEK(order_date, 1) = YEARWEEK(CURDATE(), 1) - 1
                """)
            elif filter == 'this_month':
                cursor.execute("""
                    SELECT id, user_id, total_amount, order_date
                    FROM orders
                    WHERE YEAR(order_date) = YEAR(CURDATE()) AND MONTH(order_date) = MONTH(CURDATE())
                """)
            elif filter == 'last_month':
                cursor.execute("""
                    SELECT id, user_id, total_amount, order_date
                    FROM orders
                    WHERE YEAR(order_date) = YEAR(CURDATE()) AND MONTH(order_date) = MONTH(CURDATE()) - 1
                """)
            elif filter.startswith('custom:'):
                custom_date = filter.split(':')[1]
                cursor.execute("""
                    SELECT id, user_id, total_amount, order_date
                    FROM orders
                    WHERE DATE(order_date) = %s
                """, (custom_date,))
            else:
                cursor.execute("""
                    SELECT id, user_id, total_amount, order_date
                    FROM orders
                """)

            transactions = cursor.fetchall()

        return jsonify(transactions), 200

    except Exception as e:
        print(f"Lỗi lấy dữ liệu giao dịch: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500


@app.route('/api/transactions/<int:transaction_id>', methods=['GET'])
@login_required
def get_transaction_details(transaction_id):
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT oi.product_id, oi.quantity, oi.price, p.name
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (transaction_id,))
            transaction_details = cursor.fetchall()

        return jsonify({'products': transaction_details}), 200

    except Exception as e:
        print(f"Lỗi lấy chi tiết giao dịch: {e}")
        return jsonify({'message': 'Đã có lỗi xảy ra'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)