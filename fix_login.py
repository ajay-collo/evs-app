with open('/home/ajay/evs/templates/login.html', 'r') as f:
    content = f.read()

if 'alert(' in content:
    print("Found old code! Fixing...")
    start = content.find('    function handleLogin(event, role) {')
    end   = content.find('\n    }', start) + 6
    new_func = '''    function handleLogin(event, role) {
        event.preventDefault();
        document.querySelectorAll(".error-box").forEach(e => e.remove());
        const form            = event.target;
        const btn             = form.querySelector("button[type=submit]");
        const identifierField = form.querySelector("input[type=text], input[type=email]");
        const passwordField   = form.querySelector("input[type=password]");
        const identifier      = identifierField.value.trim();
        const password        = passwordField.value;
        btn.textContent = "Logging in...";
        btn.disabled    = true;
        fetch("/login", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ role, identifier, password })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                btn.textContent = "Redirecting...";
                window.location.href = data.redirect;
            } else {
                const err = document.createElement("div");
                err.style.cssText = "background:#fff0f0;border-left:4px solid #a32d2d;color:#a32d2d;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:14px;";
                err.textContent = data.message || "Login failed.";
                form.insertBefore(err, form.firstChild);
                btn.textContent = "Try again";
                btn.disabled    = false;
            }
        })
        .catch(() => {
            const err = document.createElement("div");
            err.style.cssText = "background:#fff0f0;border-left:4px solid #a32d2d;color:#a32d2d;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:14px;";
            err.textContent = "Cannot connect to server. Is Flask running?";
            form.insertBefore(err, form.firstChild);
            btn.textContent = "Try again";
            btn.disabled    = false;
        });
    }'''
    content = content[:start] + new_func + content[end:]
    with open('/home/ajay/evs/templates/login.html', 'w') as f:
        f.write(content)
    print("✅ login.html fixed successfully!")
else:
    print("✅ No alert() found — already fixed!")
