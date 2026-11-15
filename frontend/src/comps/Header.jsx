
import "./Header.css";

export default function Header() {
  return (
    <div className="header">
      <img src="../utill/logo.jpg" alt="Logo" className="logo" width="60" />
      <h2>TerraWise, Your Smart Farming Companion</h2>
      <nav>
        <a href="/" style={{ fontWeight: 'bold' }}>Home</a>
        <a href="/about" style={{ fontWeight: 'bold' }}>About</a>
        <a href="/contact" style={{ fontWeight: 'bold' }}>Contact</a>
      </nav>
    </div>
  );
}
