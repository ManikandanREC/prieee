document.addEventListener("DOMContentLoaded", function () {
    console.log("Dashboard Loaded");

    function searchProduct() {
        let query = document.getElementById("searchBox").value.toLowerCase();
        let cards = document.querySelectorAll(".product-card");

        cards.forEach(card => {
            let name = card.querySelector("h3").textContent.toLowerCase();
            card.style.display = query === "" || name.includes(query) ? "block" : "none";
        });
    }

    document.getElementById("searchBox").addEventListener("input", searchProduct);

    // Ensure Particles.js loads after DOM is ready
    setTimeout(() => {
        if (typeof particlesJS !== "undefined") {
            particlesJS("particles-js", {
                particles: {
                    number: { value: 50 },
                    shape: {
                        type: "image",
                        image: { 
                            src: "https://cdn-icons-png.flaticon.com/512/2331/2331942.png", 
                            width: 100, 
                            height: 100 
                        }
                    },
                    size: { value: 20 },
                    move: { speed: 2 },
                    opacity: { value: 0.7 }
                }
            });
        } else {
            console.error("⚠️ Particles.js library not loaded!");
        }
    }, 500);
});
