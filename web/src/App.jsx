import { useState } from "react";
import { motion } from "motion/react";
import { APK_URL, REPO_URL, RELEASE_URL, DONATIONS, FEATURES, STEPS, SUPPORT_LINKS } from "./data.js";

const APP_PATH = `${import.meta.env.BASE_URL}app/`;

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.6, delay: i * 0.08, ease: "easeOut" } }),
};

function Reveal({ children, delay = 0, className }) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, amount: 0.2 }}
      variants={fadeUp}
      custom={delay}
    >
      {children}
    </motion.div>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };
  return (
    <button className="btn ghost small" onClick={copy}>
      {copied ? "¡Copiado!" : "Copiar"}
    </button>
  );
}

export default function App() {
  return (
    <>
      <header className="nav">
        <a className="brand" href="#top">SCREEN OCR</a>
        <nav>
          <a href="#features">Funciones</a>
          <a href="#how">Cómo funciona</a>
          <a href="#en-linea">En línea</a>
          <a href="#apoyar">Apoyar</a>
          <a href="#donar">Donar</a>
        </nav>
      </header>

      <main id="top">
        <section className="hero">
          <motion.img
            src="/ScreenOCR/icon-512.png"
            alt="Icono de ScreenOCR"
            className="hero-icon"
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
          <motion.h1 initial="hidden" animate="show" variants={fadeUp} custom={0.1}>
            Captura el texto de cualquier pantalla.
          </motion.h1>
          <motion.p className="lead" initial="hidden" animate="show" variants={fadeUp} custom={0.2}>
            ScreenOCR lee texto en inglés y español desde capturas o fotos. Gratis, sin cuentas y con tu
            texto siempre editable.
          </motion.p>
          <motion.div className="cta" initial="hidden" animate="show" variants={fadeUp} custom={0.3}>
            <a className="btn primary" href={APK_URL} download>
              Descargar para Android
            </a>
            <a className="btn ghost" href={RELEASE_URL}>
              Ver versión 1.0.0
            </a>
          </motion.div>
          <p className="fine">Android 1.0.0 · APK firmada · Windows: próximamente</p>
        </section>

        <section className="shots">
          <Reveal>
            <figure>
              <img src="/ScreenOCR/shots/app-home.png" alt="Pantalla principal de ScreenOCR en Android" />
              <figcaption>Inicio</figcaption>
            </figure>
          </Reveal>
          <Reveal delay={1}>
            <figure>
              <img src="/ScreenOCR/shots/ocr-result.png" alt="Texto extraído de una captura con inglés y español" />
              <figcaption>Texto en inglés y español</figcaption>
            </figure>
          </Reveal>
        </section>

        <section id="features" className="section">
          <Reveal>
            <h2 className="eyebrow">FUNCIONES</h2>
          </Reveal>
          <div className="grid">
            {FEATURES.map((f, i) => (
              <Reveal key={f.title} delay={i}>
                <article className="card">
                  <h3>{f.title}</h3>
                  <p>{f.text}</p>
                </article>
              </Reveal>
            ))}
          </div>
        </section>

        <section id="how" className="section">
          <Reveal>
            <h2 className="eyebrow">CÓMO FUNCIONA</h2>
          </Reveal>
          <div className="steps">
            {STEPS.map((s, i) => (
              <Reveal key={s.n} delay={i}>
                <div className="step">
                  <span className="num">{s.n}</span>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        <section id="en-linea" className="section online">
          <Reveal>
            <h2 className="eyebrow">USAR EN LÍNEA</h2>
            <p className="lead">
              No necesitas instalar nada. Abre ScreenOCR en tu navegador, toma una foto o elige una imagen y
              extrae el texto. Funciona en celular y en computadora.
            </p>
          </Reveal>
          <Reveal delay={1}>
            <div className="phone-frame">
              <iframe
                src={APP_PATH}
                title="ScreenOCR en línea"
                allow="camera"
                loading="lazy"
              />
            </div>
            <div className="online-actions">
              <a className="btn primary" href={APP_PATH} target="_blank" rel="noopener">
                Abrir en pantalla completa
              </a>
            </div>
            <p className="fine">
              La lectura usa OCR.space y necesita internet. Para tu propia clave, ábrela y entra en AJUSTES.
            </p>
          </Reveal>
        </section>

        <section id="apoyar" className="section">
          <Reveal>
            <h2 className="eyebrow">APOYAR EL DESARROLLO</h2>
            <p className="lead">
              ScreenOCR es gratis y de código abierto. Estas son las formas más sencillas de ayudar.
            </p>
          </Reveal>
          <div className="grid support">
            {SUPPORT_LINKS.map((s, i) => (
              <Reveal key={s.title} delay={i}>
                <article className="card">
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                  <a className="card-link" href={s.href} target="_blank" rel="noopener">
                    {s.label} →
                  </a>
                </article>
              </Reveal>
            ))}
          </div>
        </section>

        <section className="download">
          <Reveal>
            <h2>Instálala en tu celular</h2>
            <p className="lead">
              Abre esta página en tu celular, descarga el APK y permite "Instalar apps desconocidas" para tu
              navegador.
            </p>
            <a className="btn primary" href={APK_URL} download>
              Descargar ScreenOCR-1.0.0.apk
            </a>
            <p className="fine">
              Código abierto: <a href={REPO_URL}>{REPO_URL.replace("https://", "")}</a>
            </p>
          </Reveal>
        </section>

        <section id="donar" className="section donate">
          <Reveal>
            <h2 className="eyebrow">DONAR</h2>
            <p className="lead">
              ScreenOCR es gratis. Si te ahorra tiempo, puedes apoyar su desarrollo con una donación voluntaria.
            </p>
          </Reveal>
          <div className="donations">
            {DONATIONS.map((d, i) => (
              <Reveal key={d.symbol} delay={i}>
                <div className="donation">
                  <div className="donation-head">
                    <span className="coin">{d.name}</span>
                    <span className="symbol">{d.symbol}</span>
                  </div>
                  <code>{d.address}</code>
                  <CopyButton text={d.address} />
                </div>
              </Reveal>
            ))}
          </div>
        </section>
      </main>

      <footer>
        <span>
          © 2026 ScreenOCR · Código abierto · Hecho por <strong>XHumanX &amp; IA</strong>
        </span>
        <span>
          <a href={REPO_URL}>GitHub</a> · <a href={RELEASE_URL}>Releases</a>
        </span>
      </footer>
    </>
  );
}
