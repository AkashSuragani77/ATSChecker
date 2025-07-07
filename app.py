import os
import re
from flask import Flask, request, render_template
import pdfplumber
import spacy
from collections import defaultdict

app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")

# Skills with +10 weight increase
skills_weights = {
    'python': 13, 'machine learning': 13, 'ml': 13, 'nlp': 13, 'natural language processing': 13,
    'sql': 12, 'mysql': 12, 'postgresql': 12, 'aws': 12, 'azure': 12, 'gcp': 12,
    'tensorflow': 12, 'pytorch': 12, 'docker': 12, 'kubernetes': 12, 'pandas': 11,
    'numpy': 11, 'scikit-learn': 12, 'keras': 11, 'deep learning': 12,
    'java': 11.5, 'c++': 11.5, 'c#': 11.5, 'javascript': 12, 'js': 12,
    'typescript': 12, 'react': 12, 'react.js': 12, 'angular': 12, 'vue.js': 11.5,
    'node.js': 12, 'express.js': 11.5, 'next.js': 11.5, 'mongodb': 11.5, 'firebase': 11.5,
    'html': 11, 'css': 11, 'tailwind css': 11, 'bootstrap': 11, 'git': 11,
    'github': 11, 'bitbucket': 11, 'linux': 11, 'bash': 11, 'vs code': 11,
    'visual studio': 11, 'jupyter': 11, 'rest api': 12, 'graphql': 11,
    'flask': 12, 'django': 12
}

# Bonus keywords with +10 weights
bonus_keywords = {
    'project': 15, 'projects': 15, 'capstone': 14, 'portfolio': 13,
    'internship': 14, 'intern': 14, 'certification': 14, 'certified': 14,
    'achievement': 13, 'award': 13, 'publication': 13, 'research': 14,
    'paper': 12, 'journal': 12, 'volunteer': 12, 'hackathon': 14,
    'contribution': 13, 'opensource': 13, 'open source': 13,
    'freelance': 12, 'startup': 12, 'leadership': 12, 'mentorship': 12,
    'training': 12, 'bootcamp': 13, 'case study': 12, 'github link': 12,
    'linkedin': 11, 'medium': 11
}

def extract_text_from_pdf(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.lower()

def extract_skills(text):
    found_skills = defaultdict(int)
    for skill in skills_weights:
        pattern = re.compile(r'\b' + re.escape(skill.lower()) + r'\b')
        matches = pattern.findall(text)
        if matches:
            found_skills[skill] += len(matches)
    return found_skills

def extract_bonus(text):
    doc = nlp(text)
    bonus_score = 0
    for token in doc:
        if token.lemma_ in bonus_keywords:
            bonus_score += bonus_keywords[token.lemma_]
    return min(bonus_score, 200)

def extract_experience_years(text):
    matches = re.findall(r'(\d+)\+?\s+(?:years?|yrs?)\s+(?:of\s+)?experience', text)
    return sum(int(match) for match in matches)

def evaluate_grammar(text):
    sentences = re.split(r'[.!?]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)

    if 8 <= avg_len <= 25:
        return 20
    elif 6 <= avg_len <= 30:
        return 15
    elif 4 <= avg_len <= 35:
        return 10
    else:
        return 5

def evaluate_template(text):
    keywords = ['education', 'experience', 'skills', 'projects', 'certifications', 'summary', 'contact']
    matched = sum(1 for k in keywords if k in text.lower())
    return min(matched * 3, 20)

def education_bonus(text):
    education_keywords = [
        "btech", "b.tech", "bachelor of technology",
        "intermediate", "12th", "higher secondary",
        "10th", "ssc", "secondary school"
    ]
    if any(keyword in text for keyword in education_keywords):
        return 20
    return 0

def calculate_score(found_skills, text):
    skill_score = sum(skills_weights.get(skill, 0) * count for skill, count in found_skills.items())
    max_skill_score = sum(skills_weights.values()) * 3

    bonus_score = extract_bonus(text)
    max_bonus_score = 200

    exp_years = extract_experience_years(text)
    exp_score = min(exp_years * 0.2, 3)

    grammar_score = evaluate_grammar(text)
    template_score = evaluate_template(text)
    edu_score = education_bonus(text)

    normalized_skill = min(skill_score / max_skill_score, 1) * 20
    normalized_bonus = min(bonus_score / max_bonus_score, 1) * 17

    total_score = normalized_skill + normalized_bonus + exp_score + grammar_score + template_score + edu_score
    total_score = min(total_score, 100)

    return round(total_score / 10) * 10, grammar_score, template_score, edu_score

def get_feedback(score):
    if score < 40:
        return "😐 Improve your skills, education info, and grammar to enhance your resume."
    elif 40 <= score < 60:
        return "🙂 Good start! Add more structure and clarity to your resume."
    elif 60 <= score < 80:
        return "😄 Great! Your resume has strong content and good formatting."
    else:
        return "🚀 Outstanding! Your resume is very well structured and polished."

def generate_suggestions(score, grammar_score, template_score, edu_score, experience, bonus_points):
    suggestions = []

    if grammar_score < 15:
        suggestions.append("✍️ Use proper grammar and sentence length. Avoid long or fragmented sentences.")

    if template_score < 15:
        suggestions.append("📄 Structure your resume using standard sections: Skills, Projects, Education, etc.")

    if edu_score == 0:
        suggestions.append("🎓 Add your education details (e.g., B.Tech, Intermediate, SSC) clearly.")

    if experience == 0:
        suggestions.append("💼 Mention your experience clearly, like '2 years of experience in...'.")

    if bonus_points < 100:
        suggestions.append("🏆 Include internships, certifications, open-source, or leadership activities.")

    if score < 100:
        suggestions.append("🔧 Add more relevant technical skills (e.g., SQL, React, Docker) to improve your score.")

    return suggestions

@app.route("/", methods=["GET", "POST"])
def upload_resume():
    score = None
    experience = 0
    bonus_points = 0
    feedback = ""
    grammar_score = 0
    template_score = 0
    edu_score = 0
    suggestions = []
    upload_message = "📤 Upload your resume"

    if request.method == "POST":
        if "resume" not in request.files:
            return "No file part"
        file = request.files["resume"]
        if file.filename == "":
            return "No selected file"

        resume_text = extract_text_from_pdf(file)
        found_skills = extract_skills(resume_text)
        experience = extract_experience_years(resume_text)
        bonus_points = extract_bonus(resume_text)
        score, grammar_score, template_score, edu_score = calculate_score(found_skills, resume_text)
        feedback = get_feedback(score)
        suggestions = generate_suggestions(score, grammar_score, template_score, edu_score, experience, bonus_points)
        upload_message = "✅ Resume uploaded and analyzed"

    return render_template("index.html", score=score, experience=experience,
                           bonus_points=bonus_points, feedback=feedback,
                           grammar_score=grammar_score, template_score=template_score,
                           edu_score=edu_score, suggestions=suggestions,
                           upload_message=upload_message)

if __name__ == "__main__":
    app.run(debug=True)
