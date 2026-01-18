# NGO Donation System

A Flask-based web application for managing NGO donations with role-based access for Admins and Users.
Includes authentication, mock OTP password recovery, Razorpay (test mode) payments, dashboards, and downloadable reports.

---

## Features

### Authentication & Roles
- User registration and login
- Role-based access:
  - Emails ending with `@ngo.com` → Admin
  - All other emails → User
- Mock OTP-based password reset
- Session-based authentication

---

### Admin Dashboard
Admins are redirected to the admin dashboard after login.

Admins can:
- View total registered users
- View today’s registrations
- View donation statistics:
  - Total donations
  - Today’s donations
  - Number of donations
  - Total amount collected (₹)
- View registered users table
- View donations table
- Search users by:
  - Name
  - Email
  - Address
- Download CSV files for:
  - Registered users
  - Donations

All admin-related files follow the naming convention:
- `admin_*.html`
- `admin_*.css`

---

### User Dashboard
Normal users are redirected to the user dashboard after login.

Users can:
- View their profile details
- Make donations using Razorpay (test mode)
- View donation history
- Logout securely

---

### Payments (Razorpay – Test Mode)
- Razorpay checkout integration
- Runs in test mode only
- Supports Indian cards and net banking
- Use Net Banking for testing
- Both successful and failed payments are stored in the database

---

## Tech Stack
- Backend: Python (Flask)
- Frontend: HTML, CSS, Jinja2
- Database: SQLite
- Payments: Razorpay (Test Mode)
- Version Control: Git & GitHub

---

## Project Structure

ngo_donation_system/
│
├── app.py
├── create_db.py
├── database.db
│
├── templates/
│ ├── admin.html
│ ├── admin_users.html
│ ├── admin_donations.html
│ ├── dashboard.html
│ ├── history.html
│ ├── login.html
│ ├── auth.html
│ ├── reset_password.html
│ └── verify_otp.html
│
├── static/
│ ├── 
│ │ ├── admin_*.css
│ │ └── style.css
│ │
│ ├── 
│ │ └── payment.js
│ │
│ └── images/
│ ├── poverty.jpeg
│ ├── collage.png
│ ├── poorchild.jpeg
│ └── logo.png


## How to Run the Project

### 1. Clone the Repository
git clone <repository-link>
cd ngo_donation_system

---

### 2. Create the Database (Run Once)
python create_db.py

---

### 3. Run the Application
python app.py


---

## Application Flow
1. Register a new user
2. Login
3. Role is assigned based on email:
   - `@ngo.com` → Admin
   - Others → User
4. Admins access the admin dashboard
5. Users access the user dashboard
6. Donations are made via Razorpay (test mode)
7. Donation history is stored and viewable

---

## Password Reset Flow
1. Click Forgot Password
2. Enter registered email
3. Mock OTP is generated
4. Verify OTP
5. Regain access to account

Related files:
- `reset_password.html`
- `verify_otp.html`
Routes are defined in `app.py`.





