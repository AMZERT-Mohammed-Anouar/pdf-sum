const express = require("express");
const axios = require("axios");
const path = require("path");
const multer = require("multer");

const app = express();
app.use(express.json());

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

app.use(express.static(path.join(__dirname, 'public')));

app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'client.html'));
});

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
        const response = await axios.post("http://127.0.0.1:5000/search", { query });
        console.log("Response from Flask backend:", response.data);

        // Send the data back to the client
        res.json(response.data);
    } catch (error) {
        console.error("Error communicating with the Flask backend:", error.message);
        if (error.response) {
            console.error("Flask response data:", error.response.data);
        }
        res.status(500).json({ error: "Error communicating with the Flask backend." });
    }
});


app.post("/summarize", async (req, res) => {
    console.log("Received request to summarize the latest file.");
    try {
        const response = await axios.post("http://127.0.0.1:5000/summarize");
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
