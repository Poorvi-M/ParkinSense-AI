// ===================================
// ParkinSense AI - Audio History Page
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
        "login.html";
}


// ===================================
// Load Audio History
// ===================================

async function loadAudioHistory() {

    const tableBody =
        document.getElementById(
            "audioTableBody"
        );

    try {

        const response = await fetch(
            `${API_BASE_URL}/audio/me`,
            {
                headers: {
                    Authorization:
                        `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {

            throw new Error(
                "Unable to fetch audio history"
            );
        }

        const audioFiles =
            await response.json();

        if (!audioFiles ||
            audioFiles.length === 0) {

            tableBody.innerHTML = `

                <tr>

                    <td colspan="4">

                        No audio files found

                    </td>

                </tr>

            `;

            return;
        }

        tableBody.innerHTML = "";

        audioFiles.forEach(file => {

            tableBody.innerHTML += `

                <tr>

                    <td>
                        ${file.id}
                    </td>

                    <td>
                        ${file.file_name}
                    </td>

                    <td>
                        ${file.upload_status}
                    </td>

                    <td>

                        ${new Date(
                            file.created_at
                        ).toLocaleDateString()}

                    </td>

                </tr>

            `;
        });

    }

    catch (error) {

        console.error(
            "Audio History Error:",
            error
        );

        tableBody.innerHTML = `

            <tr>

                <td colspan="4">

                    Unable to load audio history

                </td>

            </tr>

        `;
    }

}


// ===================================
// Initialize Page
// ===================================

document.addEventListener(
    "DOMContentLoaded",
    loadAudioHistory
);