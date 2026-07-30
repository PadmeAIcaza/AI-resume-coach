document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("textarea[maxlength]").forEach((field) => {
        const counter = document.createElement("p");
        counter.className = "character-counter";
        counter.setAttribute("aria-live", "polite");
        const update = () => {
            const limit = Number(field.maxLength);
            counter.textContent = `${field.value.length.toLocaleString()} / ${limit.toLocaleString()} characters`;
            counter.classList.toggle("near-limit", limit - field.value.length <= Math.min(500, limit * 0.1));
        };
        field.insertAdjacentElement("afterend", counter);
        field.addEventListener("input", update);
        update();
    });

    document.querySelectorAll("form[data-loading-text]").forEach((form) => {
        form.addEventListener("submit", () => {
            if (!form.checkValidity()) return;
            const button = form.querySelector('button[type="submit"]');
            if (!button) return;
            button.innerHTML = `<span class="spinner" aria-hidden="true"></span>${form.dataset.loadingText}`;
            button.disabled = true;
            button.setAttribute("aria-busy", "true");
        });
    });

    const upload = document.getElementById("resume_file");
    const preview = document.getElementById("file-preview");
    if (upload && preview) {
        const reset = () => {
            upload.value = "";
            preview.hidden = true;
        };
        upload.addEventListener("change", () => {
            const file = upload.files[0];
            if (!file) return reset();
            preview.querySelector("[data-file-name]").textContent = file.name;
            preview.querySelector("[data-file-size]").textContent = `${(file.size / 1048576).toFixed(2)} MB PDF`;
            preview.hidden = false;
            const resume = document.getElementById("resume");
            if (resume) {
                resume.value = "";
                resume.dispatchEvent(new Event("input"));
            }
        });
        preview.querySelector("[data-clear-file]")?.addEventListener("click", reset);
    }

    requestAnimationFrame(() => {
        document.querySelectorAll(".score-track span[data-score]").forEach((bar) => {
            bar.style.width = `${Math.max(0, Math.min(100, Number(bar.dataset.score)))}%`;
        });
    });
});
