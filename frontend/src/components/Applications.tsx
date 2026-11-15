import { Fish, Plane, Sprout, Siren, Landmark, Microscope } from "lucide-react";

const applications = [
  {
    icon: Fish,
    title: "Fisheries & marine",
    text: "Future validated ocean datasets could support research into marine environmental variability. The current air-temperature record does not measure sea temperature or support fishing recommendations.",
  },
  {
    icon: Plane,
    title: "Aviation",
    text: "Future validated atmospheric datasets could support historical climate context for aviation research and planning. Operational flight, weather and safety decisions require certified services.",
  },
  {
    icon: Sprout,
    title: "Agriculture",
    text: "Historical precipitation and temperature provide environmental context. Future soil and vegetation datasets could extend research; crop-specific assessments require local validation.",
  },
  {
    icon: Siren,
    title: "Disaster management",
    text: "Future validated hazard and exposure datasets could support retrospective risk research and preparedness planning. Alerts and emergency decisions require dedicated operational systems.",
  },
  {
    icon: Landmark,
    title: "Government & communities",
    text: "Future validated environmental indicators could inform adaptation planning and public understanding, with geographic uncertainty and local context made explicit.",
  },
  {
    icon: Microscope,
    title: "Science & education",
    text: "Future independently approved datasets could extend reproducible comparisons for scientists, agencies, researchers, educators and students, with transparent provenance and methods.",
  },
];

export function Applications() {
  return (
    <section
      id="applications"
      className="applications"
      aria-labelledby="applications-title"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">One platform, many perspectives</p>
          <h2 id="applications-title">Earth intelligence across sectors</h2>
        </div>
        <span className="planned-tag">Planned capabilities</span>
      </div>
      <p className="applications-intro">
        A shared scientific workspace for people who work with—and depend on—the
        environment. These applications describe future possibilities; sector
        datasets, indicators and decision tools are not implemented in this MVP.
      </p>
      <div className="applications-grid">
        {applications.map(({ icon: Icon, title, text }) => (
          <article key={title}>
            <div className="application-icon">
              <Icon size={22} aria-hidden="true" />
            </div>
            <div>
              <span className="planned-label">Planned</span>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
