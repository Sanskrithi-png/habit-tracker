function toggleTheme(){
  document.body.classList.toggle("dark");
  localStorage.setItem("theme", document.body.classList.contains("dark"));
}
window.onload = () => {
  if(localStorage.getItem("theme")==="true")
    document.body.classList.add("dark");
};
