/**
 * Dynamic Pricing & Lead Submission Module
 */

// Central state configuration to avoid raw DOM reading everywhere
const state = {
    isSubmitting: false,
};

/**
 * 1. Calculate UI Price Preview
 * Note: Used purely for user presentation. Backend re-calculates actual total.
 */
function calculateTotal() {
    const vehicleSelect = document.getElementById("vehicleType");
    const packageSelect = document.getElementById("packageType");
    
    // Safely parse values with fallbacks to 0
    const vehicleBase = parseFloat(vehicleSelect?.value) || 0;
    const packageCost = parseFloat(packageSelect?.value) || 0;

    // Dynamic query for all selected add-ons (scalable for future add-ons)
    const checkedAddons = Array.from(
        document.querySelectorAll('input[name="addons"]:checked')
    );
    
    const addonsTotal = checkedAddons.reduce((sum, el) => {
        return sum + (parseFloat(el.value) || 0);
    }, 0);

    const grandTotal = vehicleBase + packageCost + addonsTotal;

    // Display formatted price
    const priceDisplay = document.getElementById("totalPrice");
    if (priceDisplay) {
        priceDisplay.innerText = new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(grandTotal);
    }
}

/**
 * 2. Submit Lead to API safely
 */
async function submitLead(event) {
    event.preventDefault();

    if (state.isSubmitting) return; // Prevent double submission

    const submitBtn = document.getElementById("submitBtn");
    const errorMessage = document.getElementById("errorMessage");

    // Gather raw selections (not pre-calculated prices or parsed text)
    const selectedAddons = Array.from(
        document.querySelectorAll('input[name="addons"]:checked')
    ).map(el => el.id);

    const payload = {
        name: document.getElementById("clientName").value.trim(),
        email: document.getElementById("clientEmail").value.trim(),
        vehicle_type: document.getElementById("vehicleType").value,
        package_type: document.getElementById("packageType").value,
        addons: selectedAddons,
        timestamp: new Date().toISOString()
    };

    // basic client-side validation check
    if (!payload.name || !payload.email || !payload.vehicle_type || !payload.package_type) {
        alert("Please complete all required fields.");
        return;
    }

    try {
        setLoadingState(true, submitBtn);

        // Relative pathing for seamless deployment across dev/staging/prod
        const response = await fetch("/api/quote", {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || "Failed to submit quote request.");
        }

        // Handle Success UI Transition
        showSuccessState();

    } catch (error) {
        console.error("Lead Submission Error:", error);
        if (errorMessage) {
            errorMessage.innerText = error.message || "Something went wrong. Please try again.";
            errorMessage.style.display = "block";
        } else {
            alert(error.message || "Failed to connect to the booking server.");
        }
    } finally {
        setLoadingState(false, submitBtn);
    }
}

// UI Helpers
function setLoadingState(isLoading, button) {
    state.isSubmitting = isLoading;
    if (!button) return;
    button.disabled = isLoading;
    button.innerText = isLoading ? "Calculating & Booking..." : "Get Instant Quote";
}

function showSuccessState() {
    const form = document.getElementById("leadForm");
    const successMsg = document.getElementById("successMessage");
    
    if (form) form.style.display = "none";
    if (successMsg) successMsg.style.display = "block";
}

// Attach Event Listeners on DOM Load
document.addEventListener("DOMContentLoaded", () => {
    // Recalculate on input changes
    document.getElementById("quoteForm")?.addEventListener("change", calculateTotal);
    document.getElementById("quoteForm")?.addEventListener("submit", submitLead);
});