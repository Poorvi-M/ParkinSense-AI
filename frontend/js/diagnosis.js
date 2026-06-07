// ===================================
// Diagnosis History Page
// ===================================

// ===================================
// Diagnosis Table Body
// ===================================

const diagnosisTableBody =
    document.getElementById(
        "diagnosisTableBody"
    );

// ===================================
// Display Placeholder Data
// ===================================

if (diagnosisTableBody) {

    diagnosisTableBody.innerHTML = `

        <tr>

            <td>
                1
            </td>

            <td>
                Awaiting ML Integration
            </td>

            <td>
                -
            </td>

        </tr>

    `;
}