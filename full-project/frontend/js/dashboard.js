// ===================================
// ParkinSense AI Dashboard Script
// ===================================


// ===================================
// Authentication Check
// ===================================

// Uncomment when authentication is fully enabled

/*
const token = localStorage.getItem("token");

if (!token) {

    alert("Please login first.");

    window.location.href = "login.html";
}
*/


// ===================================
// User Information
// ===================================

const currentUser =
    localStorage.getItem("currentUser");

const welcomeText =
    document.getElementById("welcomeText");

if (welcomeText) {

    welcomeText.innerText =
        currentUser || "User";
}


// ===================================
// Profile Circle
// ===================================

const profileCircle =
    document.getElementById("profileCircle");

if (profileCircle) {

    profileCircle.innerText =
        currentUser
            ? currentUser.charAt(0).toUpperCase()
            : "U";
}


// ===================================
// Sidebar Logout
// ===================================

const sidebarLogout =
    document.getElementById("sidebarLogout");

if (sidebarLogout) {

    sidebarLogout.addEventListener("click", () => {

        localStorage.removeItem("token");

        localStorage.removeItem("currentUser");

        window.location.href =
            "login.html";

    });

}


// ===================================
// Voice Upload Handling
// ===================================

const uploadBtn =
    document.getElementById("uploadBtn");

const uploadStatus =
    document.getElementById("uploadStatus");

const diagnosisResult =
    document.getElementById("diagnosisResult");

if (
    uploadBtn &&
    uploadStatus &&
    diagnosisResult
) {

    uploadBtn.addEventListener("click", () => {

        const audioFile =
            document.getElementById("audioFile");

        const file =
            audioFile?.files[0];

        if (!file) {

            uploadStatus.innerText =
                "Please select an audio file.";

            return;
        }

        uploadStatus.innerText =
            "Uploading audio sample...";

        // ===================================
        // Temporary Upload Simulation
        // Replace with backend API later
        // ===================================

        setTimeout(() => {

            uploadStatus.innerText =
                `Upload successful: ${file.name}`;

            diagnosisResult.innerHTML = `
                <p>Analysis Pending</p>

                <p class="sub-text">
                    Voice sample uploaded successfully.
                    Awaiting ML prediction.
                </p>
            `;

        }, 1500);

    });

}


// ===================================
// Selected File Display
// ===================================

const audioInput =
    document.getElementById("audioFile");

const selectedFile =
    document.getElementById("selectedFile");

if (
    audioInput &&
    selectedFile
) {

    audioInput.addEventListener("change", () => {

        if (
            audioInput.files &&
            audioInput.files.length > 0
        ) {

            selectedFile.textContent =
                audioInput.files[0].name;

        }

        else {

            selectedFile.textContent =
                "No file selected";
        }

    });

}


// ===================================
// End of Dashboard Script
// ===================================