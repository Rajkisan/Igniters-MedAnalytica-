from flask import Flask, render_template, redirect, url_for, request, send_file,session
import qrcode
from io import BytesIO
import hashlib
import uuid
import json
import datetime
import mysql.connector
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'your_secret_key'
class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_block(proof=1, previous_hash='0')

    def create_block(self, proof, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': str(datetime.datetime.now()),
            'proof': proof,
            'previous_hash': previous_hash,
            'prescription_content': None  # To store prescription content
        }
        self.chain.append(block)
        return block

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False
        while not check_proof:
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':  # Adjust number of leading zeros for difficulty
                check_proof = True
            else:
                new_proof += 1
        return new_proof

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
        return True

blockchain = Blockchain()

def create_connection():
    conn = mysql.connector.connect(
        host="sql6.freemysqlhosting.net",
        user="sql6700735",
        password="3Rzrjmk9pE",
        database="sql6700735"
    )
    return conn

def create_table(conn):
    sql_create_prescriptions_table = """CREATE TABLE IF NOT EXISTS prescriptions (
                                        id INT AUTO_INCREMENT PRIMARY KEY,
                                        content TEXT NOT NULL,
                                        unique_id TEXT NOT NULL,
                                        served INT DEFAULT 0
                                    );"""
    try:
        cursor = conn.cursor()
        cursor.execute(sql_create_prescriptions_table)
    except mysql.connector.Error as e:
        print(e)

def create_prescription_id():
    # Generate a unique ID using UUID and hash it
    unique_id = str(uuid.uuid4())
    hashed_id = hashlib.sha256(unique_id.encode()).hexdigest()
    return hashed_id
def send_email_gmail(prescription_content, recipient_email):
    # Set up SMTP server (Gmail in this example)
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587  # TLS Port
    sender_email = 'rajkisanssvrs@gmail.com'
    sender_password = 'fpld kblz jofn jbue'  # Consider using environment variables for security

    # Create a connection to the SMTP server
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(sender_email, sender_password)

    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = 'Prescription Details'
    msg.attach(MIMEText(f"Prescription Content:\n\n{prescription_content}", 'plain'))

    # Send email
    server.send_message(msg)

    # Quit SMTP server
    server.quit()
@app.route('/')
def index():
    return render_template('default.html')

@app.route('/generate_qr/<int:prescription_id>')
def generate_qr(prescription_id):
    conn = create_connection()
    recipient_email = session.get('recipient_email')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM prescriptions WHERE id=%s", (prescription_id,))
    prescription = cursor.fetchone()
    print(prescription)
    conn.close()

    if prescription and not prescription[3]:  # prescription exists and not served
        # Generate QR code with prescription ID encoded in the URL
        qr_data = f"https://drmav-blockchain.vercel.app/prescription?id={prescription_id}"
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        send_email_gmail("Token:\n"+prescription[2],recipient_email)
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
        cursor.execute("SELECT * FROM prescriptions WHERE id=%s", (prescription_id,))
        prescription = cursor.fetchone()

        conn.close()

        if prescription:
            return render_template('prescription.html', prescription=prescription)
        else:
            return "Prescription not found."
    else:
        return "Prescription ID not provided."

@app.route('/prescription2')
def prescription_details2():
    prescription_id = request.args.get('prescription_id')
    if prescription_id:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prescriptions WHERE id=%s", (prescription_id,))
        prescription = cursor.fetchone()

        conn.close()

        if prescription:
            return render_template('prescription2.html', prescription=prescription)
        else:
            return "Prescription not found."
    else:
        return "Prescription ID not provided."

@app.route('/mark_served/<int:prescription_id>')
def mark_served(prescription_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE prescriptions SET served=1 WHERE id=%s", (prescription_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('prescription_details2', prescription_id=prescription_id))

@app.route('/create_prescription', methods=['GET', 'POST'])
def create_prescription():
    if request.method == 'POST':
        conn = create_connection()
        cursor = conn.cursor()
        content = request.form['content']
        snos = request.form.getlist('sno')
        names = request.form.getlist('name')
        quantities = request.form.getlist('qty')
        mgs = request.form.getlist('mg')
        recipient_email = request.form['email']  # Retrieve recipient email from the form

        # Combine fields into a single string
        combined_string = f"{content}\n"

        # Check if the current blockchain is valid
        if blockchain.is_chain_valid(blockchain.chain):
            # Add prescription content to blockchain
            previous_block = blockchain.get_previous_block()
            previous_proof = previous_block['proof']
            proof = blockchain.proof_of_work(previous_proof)
            block = blockchain.create_block(proof, blockchain.hash(previous_block))
            block['prescription_content'] = combined_string
            unique_id = create_prescription_id()
            print(unique_id)
            # Add prescription content to MySQL database
            cursor.execute("INSERT INTO prescriptions (content, unique_id) VALUES (%s, %s)", (combined_string, unique_id))
            conn.commit()
            prescription_id = cursor.lastrowid
            conn.close()
            session['recipient_email'] = recipient_email
            # Send email with prescription content to recipient
            # send_email_gmail(combined_string, recipient_email)
            
            return redirect(url_for('generate_qr', prescription_id=prescription_id))
        else:
            return "Blockchain is invalid. Cannot create prescription at the moment."

    return render_template('create_prescription.html')



if __name__ == '__main__':
    create_table(create_connection())
    app.run(host='0.0.0.0', debug=True)
