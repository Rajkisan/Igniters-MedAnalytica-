from flask import Flask, render_template, redirect, url_for, request, send_file
import qrcode
from io import BytesIO
import sqlite3

app = Flask(__name__)

def create_connection():
    conn = sqlite3.connect('prescriptions.db')
    return conn

def create_table(conn):
    sql_create_prescriptions_table = """CREATE TABLE IF NOT EXISTS prescriptions (
                                        id INTEGER PRIMARY KEY,
                                        content TEXT NOT NULL,
                                        served INTEGER DEFAULT 0
                                    );"""
    try:
        c = conn.cursor()
        c.execute(sql_create_prescriptions_table)
    except sqlite3.Error as e:
        print(e)

@app.route('/')
def index():
    return render_template('default.html')

@app.route('/generate_qr/<int:prescription_id>')
def generate_qr(prescription_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prescriptions WHERE id=?", (prescription_id,))
    prescription = cursor.fetchone()
    conn.close()

    if prescription and not prescription[2]:  # prescription exists and not served
        # Generate QR code with prescription ID encoded in the URL
        qr_data = f"http://192.168.147.5:5000/prescription?id={prescription_id}"
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Save QR code image to BytesIO object
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        # Return the QR code image file
        return send_file(img_io, mimetype='image/png')
    else:
        return "Prescription does not exist or already served."

@app.route('/prescription')
def prescription_details():
    prescription_id = request.args.get('id')
    if prescription_id:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prescriptions WHERE id=?", (prescription_id,))
        prescription = cursor.fetchone()
        conn.close()

        if prescription:
            return render_template('prescription.html', prescription=prescription)
        else:
            return "Prescription not found."
    else:
        return "Prescription ID not provided."

@app.route('/mark_served/<int:prescription_id>')
def mark_served(prescription_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE prescriptions SET served=1 WHERE id=?", (prescription_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('prescription_details', id=prescription_id))

@app.route('/create_prescription', methods=['GET', 'POST'])
def create_prescription():
    if request.method == 'POST':
        conn = create_connection()
        cursor = conn.cursor()
        content = request.form['content']
        snos = request.form.getlist('sno')
        names = request.form.getlist('name')
        quantities = request.form.getlist('qty')
        print("Name",names)
        print("Content",content)
        mgs = request.form.getlist('mg')

        # Combine fields into a single string
        combined_string = f"{content}\n"

        cursor.execute("INSERT INTO prescriptions (content) VALUES (?)", (combined_string,))
        conn.commit()
        prescription_id = cursor.lastrowid
        conn.close()
        return redirect(url_for('generate_qr', prescription_id=prescription_id))
    return render_template('create_prescription.html')

if __name__ == '__main__':
    create_table(create_connection())
    app.run(host='0.0.0.0',debug=True)
