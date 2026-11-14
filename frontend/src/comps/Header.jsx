
import "./Header.css";

export default function Header() {
  return (
    <div className="header">
      <img src="../utill/logo.jpg" alt="Logo" className="logo" width="100" />
      <h2>Farm Locator</h2>
      <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
      </nav>
    </div>
  );
}
