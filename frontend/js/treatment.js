async function loadTreatments() {

    const container =
        document.getElementById(
            "treatmentContainer"
        );

    try {

        const token =
            localStorage.getItem("token");

        const response = await fetch(
            "http://localhost:8000/api/v1/treatment",
            {
                headers: {
                    Authorization:
                        `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {

            throw new Error();
        }

        const treatments =
            await response.json();

        if (
            treatments.length === 0
        ) {

            container.innerHTML = `
                <div class="card">
                    No treatment records found.
                </div>
            `;

            return;
        }

        container.innerHTML = "";

        treatments.forEach(item => {

            container.innerHTML += `

                <div class="card">

                    <h2>
                        ${item.medication_name}
                    </h2>

                    <p>
                        Dosage:
                        ${item.dosage}
                    </p>

                    <p>
                        ${item.remarks || ""}
                    </p>

                </div>
            `;
        });

    }

    catch {

        container.innerHTML = `
            <div class="card">
                Unable to load treatments.
            </div>
        `;
    }
}

loadTreatments();