// --- script.js (Enhanced with Name Passing for Emails) ---
document.addEventListener("DOMContentLoaded", () => {
    
    const uploadForm = document.getElementById("upload-form");
    const fileInput = document.getElementById("resume-file");
    const fileNameDisplay = document.getElementById("file-name");
    const submitBtn = document.getElementById("submit-btn");
    const btnText = submitBtn.querySelector(".btn-text");
    const loadingSpinner = document.getElementById("loading-spinner");
    const resultsContainer = document.getElementById("results-container");
    const errorMessage = document.getElementById("error-message");
    const introText = document.getElementById("intro-text");
    const exportBtn = document.getElementById("export-btn");
    const searchBar = document.getElementById("search-bar");

    const LABEL_ORDER = {
        "NAME": 1, "EMAIL": 2, "COLLEGE NAME": 3, "TECHNICAL SKILLS": 4
    };

    fileInput.addEventListener("change", () => {
        fileNameDisplay.textContent = fileInput.files.length > 0 ? fileInput.files[0].name : "Click to choose a file...";
        clearError();
    });

    uploadForm.addEventListener("submit", handleFormSubmit);
    searchBar.addEventListener("input", filterResumes);
    resultsContainer.addEventListener("click", handleCardAction);

    async function handleFormSubmit(e) {
        e.preventDefault();
        if (!fileInput.files.length) {
            showError("Please select a file to analyze.");
            return;
        }

        const formData = new FormData();
        formData.append("resume", fileInput.files[0]);

        setLoading(true);
        clearError();

        try {
            const response = await fetch("/process_resume", {
                method: "POST",
                body: formData,
            });
            const allResults = await response.json();
            if (!response.ok) throw new Error(allResults.error || "An unknown error occurred.");
            
            renderAllResults(allResults);

        } catch (error) {
            console.error("Upload error:", error);
            showError(error.message);
        } finally {
            setLoading(false);
            uploadForm.reset();
            fileNameDisplay.textContent = "Click to choose a file...";
        }
    }

    function filterResumes() {
        const query = searchBar.value.toLowerCase().trim();
        const cards = resultsContainer.querySelectorAll('.resume-card');

        cards.forEach(card => {
            const skills = card.dataset.skills || '';
            const isMatch = query.length > 0 && skills.split(',').some(skill => skill.toLowerCase().includes(query));
            
            card.classList.toggle('highlight', isMatch);
            card.style.order = isMatch ? '-1' : '0';
        });
    }

    function handleCardAction(e) {
        const target = e.target;
        
        if (target.classList.contains('btn-accept') || target.classList.contains('btn-reject')) {
            const card = target.closest('.resume-card');
            const email = card.dataset.email;
            const name = card.dataset.name || 'Candidate'; // Get candidate name
            const status = target.classList.contains('btn-accept') ? 'accepted' : 'rejected';
            
            if (!email) {
                alert("Cannot perform action: No email was found for this candidate.");
                return;
            }
            
            // Show confirmation dialog
            const action = status === 'accepted' ? 'accept' : 'reject';
            const confirmMsg = `Are you sure you want to ${action} ${name}?\n\nAn email will be sent to: ${email}`;
            
            if (!confirm(confirmMsg)) {
                return; // User cancelled
            }
            
            card.classList.remove('accepted', 'rejected'); 
            card.classList.add(status); 
            
            sendEmail(email, name, status, card);
        }
    }

    async function sendEmail(email, name, status, card) {
        const buttons = card.querySelectorAll('.card-actions button');
        buttons.forEach(btn => btn.disabled = true); 
        
        // Show loading state
        const actionBtn = card.querySelector(status === 'accepted' ? '.btn-accept' : '.btn-reject');
        const originalText = actionBtn.textContent;
        actionBtn.textContent = 'Sending...';
        
        try {
            const response = await fetch('/send_email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    email: email, 
                    name: name,
                    status: status 
                })
            });
            const data = await response.json();
            
            if (!response.ok) throw new Error(data.error);
            
            // Show success message
            console.log(`✅ Email sent to ${email} with status: ${status}`);
            
            // Show user-friendly notification
            const mode = data.mode === 'simulation' ? ' (Simulated)' : '';
            showSuccess(`${status === 'accepted' ? 'Acceptance' : 'Rejection'} email sent to ${name}${mode}`);
            
            // Keep buttons disabled after successful send
            actionBtn.textContent = status === 'accepted' ? '✓ Accepted' : '✗ Rejected';
            
        } catch (error) {
            console.error('Email error:', error);
            showError(`Failed to send email: ${error.message}`);
            card.classList.remove('accepted', 'rejected'); 
            buttons.forEach(btn => btn.disabled = false);
            actionBtn.textContent = originalText;
        }
    }

    function renderAllResults(resultsList) {
        resultsContainer.innerHTML = ""; 

        if (!resultsList || resultsList.length === 0) {
            introText.style.display = "block";
            exportBtn.style.display = "none";
            searchBar.style.display = "none";
            return;
        }

        introText.style.display = "none";
        exportBtn.style.display = "block";
        searchBar.style.display = "block";

        resultsList.forEach(result => {
            const card = document.createElement("div");
            card.className = "resume-card";
            
            const skillsData = (result.groups['TECHNICAL SKILLS'] || []).join(',').toLowerCase();
            const emailData = (result.groups['EMAIL'] || [''])[0];
            const nameData = (result.groups['NAME'] || ['Candidate'])[0];
            
            card.dataset.skills = skillsData;
            card.dataset.email = emailData;
            card.dataset.name = nameData; // Store name in dataset

            let tableBody = '';
            const groups = result.groups || {};
            
            const sortedLabels = Object.keys(groups).sort((a, b) => {
                return (LABEL_ORDER[a] || 100) - (LABEL_ORDER[b] || 100);
            });

            if (sortedLabels.length > 0) {
                sortedLabels.forEach(label => {
                    const items = groups[label];
                    const isSkill = label === "TECHNICAL SKILLS";
                    const itemsHtml = items.map(item => 
                        `<span class="entity-item ${isSkill ? 'skill-item' : ''}">${escapeHTML(item)}</span>`
                    ).join('');
                    tableBody += `<tr><th>${escapeHTML(label)}</th><td>${itemsHtml}</td></tr>`;
                });
            } else {
                tableBody = `<tr><td colspan="2" style="text-align:center; color:#777;">No entities found.</td></tr>`;
            }
            
            card.innerHTML = `
                <div class="card-header">
                    <h3>${escapeHTML(result.original_filename)}</h3>
                    <a href="/download/${escapeHTML(result.safe_filename)}" class="download-btn" target="_blank" title="View Original Resume">View Resume</a>
                </div>
                <div class="card-content"> 
                    <table>
                        <tbody>
                            ${tableBody}
                        </tbody>
                    </table>
                </div>
                <div class="card-actions">
                    <button class="btn-reject">Reject</button>
                    <button class="btn-accept">Accept</button>
                </div>
            `;
            
            resultsContainer.appendChild(card);
        });
    }
    
    function escapeHTML(str) {
        if (typeof str !== 'string') return '';
        return str.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m]);
    }
    
    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        btnText.classList.toggle('hidden', isLoading);
    }
    
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        errorMessage.style.color = '#e74c3c';
    }
    
    function showSuccess(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        errorMessage.style.color = '#27ae60';
        setTimeout(() => {
            errorMessage.style.display = 'none';
        }, 5000);
    }
    
    function clearError() {
        errorMessage.style.display = 'none';
    }
    
    // --- Initial Check ---
    const initialCards = resultsContainer.querySelectorAll('.resume-card').length;
    if (initialCards === 0) {
        exportBtn.style.display = "none";
        searchBar.style.display = "none";
    } else {
        exportBtn.style.display = "block";
        searchBar.style.display = "block";
        const rows = resultsContainer.querySelectorAll('tr[data-order]');
        rows.forEach(row => {
            row.style.order = row.dataset.order || 100;
        });
        const tables = resultsContainer.querySelectorAll('.card-content table tbody');
        tables.forEach(tbody => {
            tbody.style.display = 'flex';
            tbody.style.flexDirection = 'column';
        });
    }
});