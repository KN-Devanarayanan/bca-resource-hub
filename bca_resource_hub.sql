CREATE DATABASE bca_resource_hub;
use bca_resource_hub;
CREATE TABLE notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    university VARCHAR(100) NOT NULL,
    semester VARCHAR(20) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    headline VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

INSERT INTO admins (username, password_hash) VALUES (
  'admin',
  SHA2('admin123', 256)
);
USE bca_resource_hub;

SELECT * FROM admins;

USE bca_resource_hub;
SELECT * FROM notes;


CREATE TABLE syllabus (
    id INT AUTO_INCREMENT PRIMARY KEY,
    university VARCHAR(255),
    semester VARCHAR(50),
    subject VARCHAR(255),
    filename VARCHAR(255),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pyqs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    university VARCHAR(255),
    semester VARCHAR(50),
    subject VARCHAR(255),
    filename VARCHAR(255),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO syllabus (university, semester, subject, filename)
VALUES ('University of Calicut', 'Semester 1', 'English', 'calicut_sem1_english_syllabus.pdf');

INSERT INTO pyqs (university, semester, subject, filename)
VALUES ('University of Calicut', 'Semester 1', 'English', 'calicut_sem1_english_pyq.pdf');




