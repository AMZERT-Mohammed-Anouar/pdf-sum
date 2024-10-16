const express = require("express");
const axios = require("axios");
const path = require("path");
const multer = require("multer");

const app = express();
app.use(express.json());

// Configure multer for file uploads
const upload = multer({ 
    storage: multer.diskStorage({
        destination: (req, file, cb) => {
            cb(null, 'uploads/'); 
        },
        filename: (req, file, cb) => {
            cb(null, file.originalname);  
        }
    }),
    fileFilter: (req, file, cb) => {
        if (file.mimetype === 'application/pdf') {
            cb(null, true);
        } else {
            cb(new Error('File must be a PDF'));
        }
    }
});

// Serve static files (make sure 'public' directory exists with 'client.html' file)
app.use(express.static(path.join(__dirname, 'public')));

// Default route for the main page
app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'client.html')); // Ensure the file path is correct
});

// Other routes for upload and search
app.post("/upload", upload.single("pdf_file"), (req, res) => {
    if (!req.file) {
        return res.status(400).send("No file uploaded.");
    }
    console.log(`File uploaded: ${req.file.originalname}`);
    res.json({ message: "File uploaded successfully!", filename: req.file.originalname });
});

app.post("/search", async (req, res) => {
    const { query } = req.body;
    console.log(`Received query from client: ${query}`);
    try {
        const response = await axios.post("http://localhost:5000/search", { query });
        console.log("Response from Flask backend:", response.data);
        res.json(response.data);
    } catch (error) {
        console.error("Error communicating with the Flask backend:", error.message);
        if (error.response) {
            console.error("Flask response data:", error.response.data);
        }
        res.status(500).json({ error: "Error communicating with the Flask backend." });
    }
});

app.listen(3001, () => {
    console.log("Server running on http://localhost:3001");
});
