// ===================================
// ParkinSense AI - Reports Page
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
// Load Reports
// ===================================

async function loadReports() {

    const container =
        document.getElementById(
            "reportsContainer"
        );

    try {

        const response = await fetch(
            `${API_BASE_URL}/reports/me`,
            {
                headers: {
                    Authorization:
                        `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {

            throw new Error(
                "Failed to load reports"
            );
        }

        const reports =
            await response.json();

        if (!reports || reports.length === 0) {

            container.innerHTML = `

                <div class="card">

                    <h2>No Reports Available</h2>

                    <p>
                        Reports will appear here
                        after voice analysis is completed.
                    </p>

                </div>

            `;

            return;
        }

        container.innerHTML = "";

        reports.forEach(report => {

            container.innerHTML += `

                <div class="card report-card">

                    <h3>
                        ${report.report_title}
                    </h3>

                    <p>
                        ${report.report_content}
                    </p>

                    <small>

                        Generated on
                        ${new Date(
                            report.created_at
                        ).toLocaleDateString()}

                    </small>

                </div>

            `;
        });

    }

    catch (error) {

        console.error(
            "Reports Error:",
            error
        );

        container.innerHTML = `

            <div class="card">

                <h2>
                    Unable to Load Reports
                </h2>

                <p>
                    Please try again later
                    or verify backend connectivity.
                </p>

            </div>

        `;
    }

}


// ===================================
// Initialize Page
// ===================================

document.addEventListener(
    "DOMContentLoaded",
    loadReports
);