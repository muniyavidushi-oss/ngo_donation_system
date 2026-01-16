function makeDonation() {
    const amountInput = document.getElementById("amount");
    const amount = amountInput.value;

    if (!amount || amount <= 0) {
        alert("Please enter a valid donation amount.");
        return;
    }

    console.log("Initiating payment for amount:", amount);

    fetch(`/create_order?amount=${amount}`)
        .then(response => {
            console.log("Response status:", response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(obj => {
            console.log("Received payment data:", obj);

            // Verify all required fields are present
            if (!obj.order_id || !obj.amount) {
                console.error("Missing required fields:", obj);
                alert("Payment initialization failed: Missing required data");
                return;
            }

            var options = {
                key: obj.key_id,
                amount: obj.amount,
                currency: obj.currency || "INR",
                name: "NGO Donation",
                description: "Donation to NGO",
                order_id: obj.order_id,
                handler: function(response) {
                    console.log("Payment completed:", response);
                    // Send payment details to backend for verification
                    fetch('/payment_success', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_signature: response.razorpay_signature,
                            amount: obj.amount
                        })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.success) {
                            window.location.href = `/payment_success?order_id=${response.razorpay_order_id}&amount=${obj.amount}`;
                        } else {
                            alert("Payment verification failed");
                        }
                    })
                    .catch(err => {
                        console.error("Verification error:", err);
                        alert("Payment verification failed: " + err.message);
                    });
                },
                prefill: {
                    name: obj.name || "",
                    email: obj.email || "",
                    contact: obj.phone || ""
                },
                notes: {
                    address: obj.address || ""
                },
                theme: {
                    color: "#3399cc"
                },
                modal: {
                    ondismiss: function() {
                        console.log("Payment dismissed by user");
                        // Record failed/cancelled payment
                        fetch('/payment_failed', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                amount: obj.amount
                            })
                        })
                        .then(() => {
                            alert("Payment was cancelled");
                        })
                        .catch(err => {
                            console.error("Error recording cancelled payment:", err);
                        });
                    }
                }
            };

            console.log("Payment options:", options);

            // Check if Razorpay is loaded
            if (typeof Razorpay === 'undefined') {
                alert("Razorpay library not loaded. Please refresh the page.");
                return;
            }

            console.log("Starting Razorpay payment...");
            var rzp = new Razorpay(options);
            
            rzp.on('payment.failed', function(response) {
                console.error("Razorpay Error:", response.error);
                
                // Record failed payment
                fetch('/payment_failed', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        amount: obj.amount
                    })
                })
                .then(() => {
                    alert("Payment Failed: " + response.error.description);
                })
                .catch(err => {
                    console.error("Error recording failed payment:", err);
                    alert("Payment Failed: " + response.error.description);
                });
            });

            rzp.open();
        })
        .catch(err => {
            console.error("Fetch error:", err);
            alert("Payment failed to initialize: " + err.message);
        });
}



    