
import "./Footer.css";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-content">

        <div className="footer-brand">
          <h2>TerraWise</h2>
          <p>
            Smarter agricultural decisions through
            data, technology, and sustainability.
          </p>
        </div>

        <div className="footer-links">
          <h3>Explore</h3>
          <a href="/">Home</a>
          <a href="/#about">About Us</a>
          <a href="/#features">Features</a>
        </div>

        <div className="footer-links">
          <h3>Our Mission</h3>
          <p>Helping farmers grow smarter, save water,
            and build a more sustainable future.</p>
        </div>

      </div>

      <div className="footer-bottom">
        <p>© 2026 TerraWise. All rights reserved.</p>
        <span>Built for smarter farming</span>
      </div>
    </footer>
  );
}
