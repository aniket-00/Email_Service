function validateForm() {
    var username = document.getElementById("username").value;
    var password = document.getElementById("password").value;
    var usernameError = document.getElementById("username-error");
    var passwordError = document.getElementById("password-error");
    var isValid = true;

    usernameError.innerHTML = "";
    passwordError.innerHTML = "";

    if (username.trim() === "") {
        usernameError.innerHTML = "Username is required";
        isValid = false;
    }

    if (password.trim() === "") {
        passwordError.innerHTML = "Password is required";
        isValid = false;
    }

    return isValid;
}
