from flask import Flask, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
from flask_cors import CORS

app = Flask(__name__)

app.secret_key = 'your secret key' 

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456' 
app.config['MYSQL_DB'] = 'geeklogin'

CORS(app)

mysql = MySQL(app)

@app.route('/api/test_db')
def test_db():
    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                return jsonify({'message': 'Kết nối database thành công!'}), 200
            else:
                return jsonify({'message': 'Lỗi kết nối database'}), 500
    except Exception as e:
        print(f"Lỗi: {e}")
        return jsonify({'message': f'Lỗi: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)