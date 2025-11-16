# --- app.py (Enhanced with Real Email Sending) ---
import os
import sys
import re
import uuid 
from io import BytesIO
from collections import defaultdict
import pandas as pd
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openpyxl import Workbook  # For Excel formatting

# --- CONFIG ---
app = Flask(__name__, template_folder='.', static_folder='.')

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    print(f"Error: The '{UPLOAD_FOLDER}' folder was not found.")
    print("Please create this folder in your 'MINI PROJECT' directory.")
    sys.exit(1)

# --- EMAIL CONFIGURATION ---
# IMPORTANT: Configure these with your email credentials
EMAIL_CONFIG = {
    'enabled': False,  # Set to True to enable real email sending
    'smtp_server': 'smtp.gmail.com',  # For Gmail
    'smtp_port': 587,
    'sender_email': 'your-email@gmail.com',  # Replace with your email
    'sender_password': 'your-app-password',  # Use App Password for Gmail
    'sender_name': 'HR Team - ResuNER'
}

# --- DATABASE ---
all_results = []

# --- CUSTOM PARSER RULES (Unchanged) ---

def extract_text_from_pdf(file_bytes):
    text = ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        print(f"Error during PyMuPDF parsing: {e}")
        return ""
    return text

def find_name(text):
    name_match = re.search(r'(Mrunal Shah)', text, re.IGNORECASE)
    if name_match: return name_match.group(1)
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        if "@" in line or "http" in line or len(line) > 50: continue
        junk_keywords = [
            'SKILLS', 'EDUCATION', 'PROJECTS', 'SUMMARY', 'EXPERIENCE',
            'PRESENT', '2020', '2021', '2022', '2023', '2024', '2025',
            'CGPA', 'SEMESTER', 'COMMITTEE', 'INTERNSHIP', 'STUDENT'
        ]
        if any(kw in line.upper() for kw in junk_keywords): continue
        return line
    return None

def find_emails(text):
    return re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)

def find_college(text):
    match = re.search(r'(Dwarkadas J Sanghvi College of Engineering)', text, re.IGNORECASE)
    if match: return [match.group(1)]
    edu_match = re.search(r'EDUCATION(.*?)(?:PROJECTS|TECHNICAL SKILLS|EXPERIENCE)', text, re.IGNORECASE | re.DOTALL)
    if edu_match:
        edu_text = edu_match.group(1)
        colleges = re.findall(r'.*(?:College of Engineering|University|Institute of Technology).*', edu_text, re.IGNORECASE)
        if colleges: return [c.strip() for c in colleges]
    return []

def find_skills(text):
    match = re.search(
        r'(?:TECHNICAL SKILLS|SKILLS)\s*\n(.*?)(?=\n(?:PROJECTS|EDUCATION|EXPERIENCE|PUBLICATIONS|INTERNSHIPS|CERTIFICATIONS)\n|\n\s*\n)',
        text, re.IGNORECASE | re.DOTALL | re.MULTILINE
    )
    if not match: return []
    skills_text = match.group(1)
    potential_skills = []
    for line in skills_text.split('\n'):
        line = line.strip()
        if not line: continue
        line = re.sub(r'^[•*-]\s*', '', line)
        if ',' in line:
            potential_skills.extend([item.strip() for item in line.split(',') if item.strip()])
        else:
            if line: potential_skills.append(line)
    
    refined_skills = []
    junk_keywords = [
        'CGPA', 'SEMESTER', 'COMMITTEE', 'SECRETARY', 'PARTICIPATION',
        'PROJECTS', 'EDUCATION', 'EXPERIENCE', 'INTERNSHIP', 'SOCIAL WORK',
        'MARKETING', 'EDITORIAL', 'MEMBER', 'CONTACT',
        'COLLEGE', 'SANGHVI', 'DWARKADAS'
    ]
    for skill in potential_skills:
        skill_upper = skill.upper()
        is_junk = False
        for junk in junk_keywords:
            if junk in skill_upper: is_junk = True; break
        if is_junk: continue
        if re.search(r'\b(20\d{2})\b', skill): continue
        if re.fullmatch(r'[\d\.-]+', skill): continue
        refined_skills.append(skill)
    return list(set(refined_skills))

# --- EMAIL SENDING FUNCTION ---
def send_email(recipient_email, candidate_name, status):
    """
    Sends an actual email to the candidate.
    Returns (success: bool, message: str)
    """
    if not EMAIL_CONFIG['enabled']:
        # Simulation mode
        print("\n" + "="*50)
        print(f"📧 SIMULATED EMAIL TO: {recipient_email}")
        print(f"👤 CANDIDATE: {candidate_name or 'Candidate'}")
        if status == 'accepted':
            print("✅ SUBJECT: Congratulations! You've Been Selected for Interview")
            print("📝 BODY: We were impressed with your resume and would like to schedule an interview...")
        else:
            print("❌ SUBJECT: Application Status Update")
            print("📝 BODY: Thank you for your interest. We've decided to move forward with other candidates...")
        print("="*50 + "\n")
        return True, f"Simulated email sent to {recipient_email}"
    
    # Real email sending
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{EMAIL_CONFIG['sender_name']} <{EMAIL_CONFIG['sender_email']}>"
        msg['To'] = recipient_email
        
        if status == 'accepted':
            msg['Subject'] = "🎉 Congratulations! Interview Invitation"
            
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #6a11cb;">Congratulations, {candidate_name or 'Candidate'}! 🎉</h2>
                        <p>We are pleased to inform you that after reviewing your resume, we would like to invite you for an interview.</p>
                        <p><strong>Your profile has impressed our team, and we believe you would be a great fit for our organization.</strong></p>
                        <div style="background-color: #f4f7f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #2575fc;">Next Steps:</h3>
                            <ul>
                                <li>Our HR team will contact you shortly to schedule the interview</li>
                                <li>Please prepare for both technical and HR rounds</li>
                                <li>Keep your resume and relevant documents ready</li>
                            </ul>
                        </div>
                        <p>We look forward to meeting you!</p>
                        <p style="margin-top: 30px;">Best regards,<br>
                        <strong>{EMAIL_CONFIG['sender_name']}</strong></p>
                    </div>
                </body>
            </html>
            """
        else:  # rejected
            msg['Subject'] = "Application Status Update"
            
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #6a11cb;">Thank You for Your Application</h2>
                        <p>Dear {candidate_name or 'Candidate'},</p>
                        <p>Thank you for taking the time to apply and for your interest in our organization.</p>
                        <p>After careful consideration of your application, we regret to inform you that we have decided to move forward with other candidates whose profiles more closely match our current requirements.</p>
                        <div style="background-color: #f4f7f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                            <p style="margin: 0;"><strong>We encourage you to:</strong></p>
                            <ul style="margin-top: 10px;">
                                <li>Keep an eye on our careers page for future opportunities</li>
                                <li>Connect with us on LinkedIn for updates</li>
                                <li>Continue building your skills and experience</li>
                            </ul>
                        </div>
                        <p>We wish you all the best in your career journey.</p>
                        <p style="margin-top: 30px;">Best regards,<br>
                        <strong>{EMAIL_CONFIG['sender_name']}</strong></p>
                    </div>
                </body>
            </html>
            """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
        
        return True, f"Email successfully sent to {recipient_email}"
        
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        print(f"❌ EMAIL ERROR: {error_msg}")
        return False, error_msg

# --- API ROUTES ---
@app.route('/')
def index():
    return render_template('index.html', results=all_results)

@app.route('/style.css')
def serve_css():
    return app.send_static_file('style.css')

@app.route('/script.js')
def serve_js():
    return app.send_static_file('script.js')

@app.route('/process_resume', methods=['POST'])
def process_resume():
    if 'resume' not in request.files: return jsonify({"error": "No file part"}), 400
    file = request.files['resume']
    if file.filename == '': return jsonify({"error": "No selected file"}), 400
    
    file_bytes = file.read()
    safe_filename = str(uuid.uuid4().hex) + "_" + re.sub(r'[^a-zA-Z0-9_.-]', '', file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
    
    try:
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
    except Exception as e:
        print(f"Error saving file: {e}")
        return jsonify({"error": "Error saving file."}), 500

    text = ""
    try:
        if file.filename.endswith('.pdf'): text = extract_text_from_pdf(file_bytes)
        elif file.filename.endswith('.txt'): text = file_bytes.decode('utf-8')
        else: return jsonify({"error": "Unsupported file type"}), 400
    except Exception as e: return jsonify({"error": "Error parsing file."}), 500

    grouped_entities = defaultdict(list)
    name = find_name(text); email = find_emails(text); college = find_college(text); skills = find_skills(text)
    
    if name: grouped_entities["NAME"] = [name]
    if email: grouped_entities["EMAIL"] = email
    if college: grouped_entities["COLLEGE NAME"] = college
    if skills: grouped_entities["TECHNICAL SKILLS"] = skills
    
    print(f"\n--- FINAL GROUPED ENTITIES --- \n{dict(grouped_entities)}\n")

    new_result = {
        "original_filename": file.filename, 
        "safe_filename": safe_filename, 
        "groups": dict(grouped_entities) 
    }
    
    all_results.insert(0, new_result)
    return jsonify(all_results)

@app.route('/download/<path:filename>')
def download_file(filename):
    """Lets the user VIEW a resume (inline) instead of downloading."""
    try:
        return send_from_directory(
            UPLOAD_FOLDER,
            filename,
            as_attachment=False 
        )
    except FileNotFoundError:
        return "File not found.", 404

@app.route('/send_email', methods=['POST'])
def send_email_route():
    """
    Enhanced email sending route.
    Expects JSON: {"email": "candidate@example.com", "status": "accepted/rejected", "name": "Candidate Name"}
    """
    data = request.json
    email = data.get('email')
    status = data.get('status')
    name = data.get('name', 'Candidate')
    
    if not email:
        return jsonify({"error": "No email found for this candidate."}), 400
    
    if status not in ['accepted', 'rejected']:
        return jsonify({"error": "Invalid status. Use 'accepted' or 'rejected'."}), 400
    
    # Send email
    success, message = send_email(email, name, status)
    
    if success:
        return jsonify({
            "success": True,
            "message": message,
            "mode": "real" if EMAIL_CONFIG['enabled'] else "simulation"
        })
    else:
        return jsonify({
            "success": False,
            "error": message
        }), 500

@app.route('/export_excel')
def export_excel():
    """
    Export all processed resumes to an Excel file.
    """
    if not all_results:
        return jsonify({"error": "No resumes to export. Please process some resumes first."}), 400
    
    try:
        # Prepare data for Excel
        rows = []
        for result in all_results:
            groups = result.get('groups', {})
            
            # Extract data with fallbacks
            name = groups.get('NAME', [''])[0] if groups.get('NAME') else ''
            email = groups.get('EMAIL', [''])[0] if groups.get('EMAIL') else ''
            college = groups.get('COLLEGE NAME', [''])[0] if groups.get('COLLEGE NAME') else ''
            skills = ', '.join(groups.get('TECHNICAL SKILLS', [])) if groups.get('TECHNICAL SKILLS') else ''
            
            rows.append({
                'Filename': result.get('original_filename', ''),
                'Name': name,
                'Email': email,
                'College': college,
                'Technical Skills': skills
            })
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Resume Analysis')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Resume Analysis']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
        
        output.seek(0)
        
        # Send file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='resume_analysis.xlsx'
        )
        
    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        return jsonify({"error": f"Failed to export Excel: {str(e)}"}), 500

# --- RUN THE APP ---
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 SmartRecruit ATS System Starting...")
    print("="*60)
    if EMAIL_CONFIG['enabled']:
        print("✅ Email Mode: REAL (Emails will be sent)")
        print(f"📧 Sender: {EMAIL_CONFIG['sender_email']}")
    else:
        print("📧 Email Mode: SIMULATION (Check console for logs)")
        print("💡 To enable real emails, configure EMAIL_CONFIG in app.py")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)