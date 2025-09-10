const loginBtn = document.getElementById("login");
const signupBtn = document.getElementById("signup");
const sliderTab = document.querySelector(".slider-tab");
const formInner = document.querySelector(".form-inner");
const signupSwitch = document.getElementById("signupSwitch");
<script src="{{ url_for('static', filename='login.js') }}"></script>


signupBtn.addEventListener("click", () => {
  formInner.style.marginLeft = "-50%";
  sliderTab.style.left = "50%";
});

loginBtn.addEventListener("click", () => {
  formInner.style.marginLeft = "0%";
  sliderTab.style.left = "0%";
});


signupSwitch.addEventListener("click", (e) => {
  e.preventDefault();
  signupBtn.checked = true;
  signupBtn.dispatchEvent(new Event("click"));
});
