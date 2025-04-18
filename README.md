# Email Advertisement Detector

This Python program reads emails using POP3, detects advertisements using a Hugging Face model, and tracks unique email addresses with their last contact dates.

## Features
- POP3 email reading
- Advertisement detection using Hugging Face model
- Email address tracking with last contact dates
- Secure credential management using environment variables

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root with your email credentials:
```
EMAIL_HOST=pop.gmail.com
EMAIL_PORT=995
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_specific_password
```

Note: For Gmail, you'll need to use an App Password instead of your regular password. You can generate one in your Google Account settings under Security > 2-Step Verification > App passwords.

## Usage

Run the program:
```bash
python email_reader.py
```

The program will:
1. Connect to your email account
2. Download recent emails
3. Analyze them for advertisements
4. Store unique email addresses and their last contact dates
5. Save the results to a CSV file 