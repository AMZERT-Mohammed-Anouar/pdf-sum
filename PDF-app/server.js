const express = require("express");
const axios = require("axios");
const path = require("path");

const app = express();
app.use(express.json());

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// Default route for the main page
app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'client.html'));
});

app.post("/search", async (req, res) => {
    const { query } = req.body;  // Ensure this extracts the query correctly

    console.log(`Received query from client: ${query}`);  // Debug: print the query received

    try {
        // Forward the query to the Flask backend
        const response = await axios.post("http://localhost:5000/search", { query });
        console.log("Response from Flask backend:", response.data);  // Debug: log the response from Flask

        // Return the PDF text and extracted information to the client
        res.json({
            pdf_text: response.data.pdf_text,
            search_result: response.data.search_result,
            occurrences: response.data.occurrences,
            pages_found: response.data.pages_found,
            lines_found: response.data.lines_found
        });
    } catch (error) {
        console.error("Error communicating with the Flask backend:", error.message);  // Log the error message

        // Log detailed error response if it exists
        if (error.response) {
            console.error("Flask response data:", error.response.data);  // Log response data for debugging
        }

        res.status(500).json({ error: "Error communicating with the Flask backend." });
    }
});

// Start the server
app.listen(3001, () => {
    console.log("Server running on http://localhost:3001");
});
