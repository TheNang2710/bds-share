import os
import pandas as pd
import json
from flask import Flask, render_template, request, send_from_directory
from fpdf import FPDF
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load client mapping from environment variable
client_map = {}
mapping_env = os.environ.get('CLIENT_MAPPING')
if mapping_env:
    try:
        client_map = json.loads(mapping_env)
        print("Loaded CLIENT_MAPPING from environment.")
    except Exception as e:
        print(f"Error parsing CLIENT_MAPPING: {e}")
else:
    print("CLIENT_MAPPING environment variable not found.")

class PDF(FPDF):
    def __init__(self, client_name="", email="", start_date="", end_date=""):
        super().__init__()
        self.client_name = client_name
        self.email = email
        self.start_date = start_date
        self.end_date = end_date

    def header(self):
        # Set font for title
        self.set_font("Arial", "B", 16)
        # Center the title
        self.cell(0, 10, "API Latency Report", ln=True, align="C")
        
        # Add date range - căn giữa
        self.set_font("Arial", "", 11)
        self.cell(0, 10, f"Date Range: {self.start_date} - {self.end_date}", ln=True, align="C")
        
        # Add client info and other details
        self.cell(0, 8, f"Client: {self.client_name} ({self.email})", ln=True, align="L")
        self.cell(0, 8, "Unit: Millisecond (ms)", ln=True, align="L")
        self.cell(0, 8, "Server: Internal server in France", ln=True, align="L")
        self.ln(5)

    def footer(self):
        self.set_y(-10)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def table(self, df):
        # Column headers
        self.set_font("Arial", "B", 10)
        col_widths = [60, 30, 20, 20, 20, 20, 20]
        cols = df.columns.tolist()
        
        # Draw header cells
        for i, col in enumerate(cols):
            self.cell(col_widths[i], 10, col, border=1, align="C")
        self.ln()

        # Table data
        self.set_font("Arial", "", 10)
        for _, row in df.iterrows():
            for i, col in enumerate(cols):
                if i == 0:  # path column
                    self.cell(col_widths[i], 10, str(row[col]), border=1, align="L")
                else:  # numeric columns
                    val = "{:,}".format(round(row[col])) if isinstance(row[col], (int, float)) else str(row[col])
                    self.cell(col_widths[i], 10, val, border=1, align="R")
            self.ln()

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            df = pd.read_csv(filepath)
            parts = filename.replace('.csv', '').split('_')
            prefix = parts[0]
            start_date = parts[-2]
            end_date = parts[-1]

            client_name = client_map.get(prefix, {}).get('client_name', prefix.capitalize())
            email = client_map.get(prefix, {}).get('email', f"accounts@{prefix}.xyz")

            pdf = PDF(client_name, email, start_date, end_date)
            pdf.add_page()
            pdf.table(df)

            pdf_filename = filename.replace('.csv', '.pdf')
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
            pdf.output(pdf_path)

            return render_template('result.html', pdf_file=pdf_filename)

    return render_template('latency.html')

@app.route('/static/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
