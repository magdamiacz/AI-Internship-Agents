const express = require('express');
const bodyParser = require('body-parser');
const sqlite3 = require('sqlite3').verbose();
const nodemailer = require('nodemailer');
const app = express();
const port = 3000;

app.use(bodyParser.json());
app.use(express.static('frontend'));

// Initialize SQLite database
const db = new sqlite3.Database(':memory:');
db.serialize(() => {
    db.run('CREATE TABLE contact_submissions (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)');
});

// Email configuration
const transporter = nodemailer.createTransport({
    service: 'SendGrid',
    auth: {
        user: 'your_sendgrid_username',
        pass: 'your_sendgrid_password'
    }
});

app.post('/api/contact', (req, res) => {
    const { name, email, message } = req.body;

    // Insert into database
    db.run('INSERT INTO contact_submissions (name, email, message) VALUES (?, ?, ?)', [name, email, message], function(err) {
        if (err) {
            return res.status(500).send('Database error');
        }

        // Send email notification
        const mailOptions = {
            from: 'no-reply@yourdomain.com',
            to: 'your_email@yourdomain.com',
            subject: 'New Contact Submission',
            text: `Name: ${name}\nEmail: ${email}\nMessage: ${message}`
        };

        transporter.sendMail(mailOptions, (error, info) => {
            if (error) {
                return res.status(500).send('Email error');
            }
            res.status(200).send('Message received');
        });
    });
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});