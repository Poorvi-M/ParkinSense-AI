// ===================================
// Progression Page
// ===================================

// ===================================
// Progression Container
// ===================================

const progressionContainer =
    document.getElementById(
        "progressionContainer"
    );

// ===================================
// Display Placeholder Content
// ===================================

if (progressionContainer) {

    progressionContainer.innerHTML = `

        <div class="card">

            <h2>
                Progress Note
            </h2>

            <p>
                Progression data will appear
                after multiple severity assessments.
            </p>

            <p class="sub-text">
                Awaiting backend integration
                and historical severity records.
            </p>

        </div>

    `;
}