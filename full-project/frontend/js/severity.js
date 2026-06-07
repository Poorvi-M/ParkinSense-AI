// ===================================
// ParkinSense AI - Severity Page
// ===================================


// ===================================
// Severity Container
// ===================================

const severityContainer =
    document.getElementById(
        "severityContainer"
    );


// ===================================
// Temporary Severity Data
// Replace with backend API later
// ===================================

const severityScore = 42;


// ===================================
// Severity Classification
// ===================================

let severityLevel = "";
let severityMessage = "";

if (severityScore <= 30) {

    severityLevel = "Mild";

    severityMessage =
        "Symptoms indicate early-stage Parkinson's progression.";

}

else if (severityScore <= 70) {

    severityLevel = "Moderate";

    severityMessage =
        "Symptoms indicate moderate Parkinson's progression.";

}

else {

    severityLevel = "Severe";

    severityMessage =
        "Symptoms indicate advanced Parkinson's progression.";
}


// ===================================
// Render Severity Card
// ===================================

severityContainer.innerHTML = `

    <h1 class="severity-score">
        ${severityScore}
    </h1>

    <h3>
        ${severityLevel}
    </h3>

    <p>
        ${severityMessage}
    </p>

    <small>
        Demo Value - Awaiting ML Backend Integration
    </small>

`;