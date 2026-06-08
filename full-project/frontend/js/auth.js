// ======================================
// ParkinSense AI Authentication Script
// ======================================

// Backend API URL
// Update later if backend URL changes

const API_BASE_URL =
    "http://localhost:8000/api/v1";

// ======================================
// REGISTER
// ======================================

const registerForm =
    document.getElementById("registerForm");

if (registerForm) {

    registerForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();

            const username =
                document.getElementById("username")
                .value.trim();

            const email =
                document.getElementById("email")
                .value.trim();

            const password =
                document.getElementById("password")
                .value;

            const confirmPassword =
                document.getElementById("confirmPassword")
                .value;

            const role =
                document.getElementById("role")
                .value;

            const message =
                document.getElementById("message");

            message.innerText = "";

            // Password Length Validation

            if (password.length < 8) {

                message.innerText =
                    "Password must contain at least 8 characters";

                return;
            }

            // Confirm Password Validation

            if (password !== confirmPassword) {

                message.innerText =
                    "Passwords do not match";

                return;
            }

            try {

                const response =
                    await fetch(
                        `${API_BASE_URL}/auth/register`,
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                username,
                                email,
                                password,
                                role
                            })
                        }
                    );

                const data =
                    await response.json();

                if (response.ok) {

                    message.innerText =
                        "Registration Successful! Redirecting to login...";

                    setTimeout(() => {

                        window.location.href =
                            "index.html";

                    }, 1500);

                } else {

                    message.innerText =
                        data.detail ||
                        "Registration Failed";
                }

            } catch (error) {

                console.error(error);

                message.innerText =
                    "Backend not running. UI is working.";
            }

        }
    );

}

// ======================================
// LOGIN
// ======================================

const loginForm =
    document.getElementById("loginForm");

if (loginForm) {

    loginForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();

            const email =
                document.getElementById("loginEmail")
                .value.trim();

            const password =
                document.getElementById("loginPassword")
                .value;

            const message =
                document.getElementById("message");

            message.innerText = "";

            try {

                const response =
                    await fetch(
                        `${API_BASE_URL}/auth/login`,
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                email,
                                password
                            })
                        }
                    );

                const data =
                    await response.json();

                if (response.ok) {

                    // Store JWT Token

                    localStorage.setItem(
                        "token",
                        data.access_token
                    );

                    // Store User For Dashboard

                    localStorage.setItem(
                        "currentUser",
                        email
                    );

                    message.innerText =
                        "Login Successful! Redirecting...";

                    setTimeout(() => {

                        window.location.href =
                            "dashboard.html";

                    }, 1000);

                } else {

                    message.innerText =
                        data.detail ||
                        "Login Failed";
                }

            } catch (error) {

                console.error(error);

                message.innerText =
                    "Backend not running. UI is working.";
            }

        }
    );

}

// ======================================
// Authentication Helpers
// ======================================

function isLoggedIn() {

    const token =
        localStorage.getItem("token");

    return token !== null;
}

// ======================================
// Logout
// ======================================

function logout() {

    localStorage.removeItem("token");

    localStorage.removeItem(
        "currentUser"
    );

    window.location.href =
        "index.html";
}