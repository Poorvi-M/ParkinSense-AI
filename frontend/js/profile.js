// ===================================
// ParkinSense AI - Profile Script
// ===================================


// ===================================
// Configuration
// ===================================

const API_BASE_URL =
    "http://localhost:8000/api/v1";


// ===================================
// Authentication Check
// ===================================

const token =
    localStorage.getItem("token");

if (!token) {

    alert("Please login first.");

    window.location.href =
        "index.html";
}


// ===================================
// Load Profile Information
// ===================================

async function loadProfile() {

    try {

        const response = await fetch(
            `${API_BASE_URL}/auth/me`,
            {
                method: "GET",

                headers: {
                    Authorization: `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {

            throw new Error(
                "Failed to fetch profile data"
            );
        }

        const user =
            await response.json();

        document.getElementById("username")
            .innerText =
            user.username || "Unavailable";

        document.getElementById("email")
            .innerText =
            user.email || "Unavailable";

        document.getElementById("role")
            .innerText =
            user.role || "Unavailable";

        document.getElementById("createdAt")
            .innerText =
            user.created_at
                ? new Date(
                    user.created_at
                  ).toLocaleDateString()
                : "Unavailable";

    }

    catch (error) {

        console.error(
            "Profile Error:",
            error
        );

        document.getElementById("username")
            .innerText = "Unavailable";

        document.getElementById("email")
            .innerText = "Unavailable";

        document.getElementById("role")
            .innerText = "Unavailable";

        document.getElementById("createdAt")
            .innerText = "Unavailable";
    }
}


// ===================================
// Initialize Page
// ===================================

document.addEventListener(
    "DOMContentLoaded",
    loadProfile
);