import { useMemo, useState } from "react";

function calcBMI(heightCm, weightKg) {
  const hm = Number(heightCm) / 100;
  if (!hm || !weightKg) return "";
  return (Number(weightKg) / (hm * hm)).toFixed(1);
}

export default function SubjectStep({ subject, setSubject, onBack, onNext }) {
  const [errors, setErrors] = useState({});
  const bmi = useMemo(() => calcBMI(subject.height_cm, subject.weight_kg), [subject.height_cm, subject.weight_kg]);

  function validate() {
    const e = {};
    if (!subject.subject_name?.trim()) e.subject_name = "Required";
    if (!(subject.age_years > 0)) e.age_years = "Enter valid age";
    if (!(subject.height_cm > 0)) e.height_cm = "Enter valid height";
    if (!(subject.weight_kg > 0)) e.weight_kg = "Enter valid weight";
    if (!(subject.camera_distance_m > 0)) e.camera_distance_m = "Enter camera distance";
    if (!subject.recording_date) e.recording_date = "Select recording date";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  return (
    <div className="glass p-6 space-y-4">
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <label className="label">Subject Name</label>
          <input className="input" value={subject.subject_name}
            onChange={(e) => setSubject({ ...subject, subject_name: e.target.value })}
            placeholder="Subject 01"
          />
          {errors.subject_name && <p className="error">{errors.subject_name}</p>}
        </div>

        <div>
          <label className="label">Age (years)</label>
          <input className="input" type="number" value={subject.age_years}
            onChange={(e) => setSubject({ ...subject, age_years: Number(e.target.value) })}
          />
          {errors.age_years && <p className="error">{errors.age_years}</p>}
        </div>

        <div>
          <label className="label">Sex</label>
          <select className="input"
            value={subject.sex}
            onChange={(e) => setSubject({ ...subject, sex: e.target.value })}
          >
            <option>Male</option>
            <option>Female</option>
            <option>Other</option>
          </select>
        </div>

        <div>
          <label className="label">Recording Date</label>
          <input className="input" type="date"
            value={subject.recording_date}
            onChange={(e) => setSubject({ ...subject, recording_date: e.target.value })}
          />
          {errors.recording_date && <p className="error">{errors.recording_date}</p>}
        </div>

        <div>
          <label className="label">Height (cm)</label>
          <input className="input" type="number"
            value={subject.height_cm}
            onChange={(e) => setSubject({ ...subject, height_cm: Number(e.target.value) })}
          />
          {errors.height_cm && <p className="error">{errors.height_cm}</p>}
        </div>

        <div>
          <label className="label">Weight (kg)</label>
          <input className="input" type="number"
            value={subject.weight_kg}
            onChange={(e) => setSubject({ ...subject, weight_kg: Number(e.target.value) })}
          />
          {errors.weight_kg && <p className="error">{errors.weight_kg}</p>}
        </div>

        <div>
          <label className="label">BMI (auto)</label>
          <input className="input bg-white/5" value={bmi || ""} readOnly />
          <p className="help">Calculated from height & weight</p>
        </div>

        <div>
          <label className="label">Camera Distance (m)</label>
          <input className="input" type="number" step="0.1"
            value={subject.camera_distance_m}
            onChange={(e) => setSubject({ ...subject, camera_distance_m: Number(e.target.value) })}
          />
          {errors.camera_distance_m && <p className="error">{errors.camera_distance_m}</p>}
        </div>

        <div>
          <label className="label">Seat Reference Length (cm)</label>
          <input className="input" type="number"
            value={subject.seat_reference_length_cm}
            onChange={(e) => setSubject({ ...subject, seat_reference_length_cm: Number(e.target.value) })}
          />
          <p className="help">Use 50 if you used a 50cm ruler</p>
        </div>

        <div>
          <label className="label">Seat Reference Pixel Length (px)</label>
          <input className="input" type="number"
            value={subject.seat_reference_pixel_length}
            onChange={(e) => setSubject({ ...subject, seat_reference_pixel_length: Number(e.target.value) })}
          />
          <p className="help">Measure pixels between 0–50 cm marks</p>
        </div>
      </div>

      <div className="flex justify-between">
        <button className="btn-ghost" onClick={onBack}>Previous</button>
        <button
          className="btn-primary"
          onClick={() => validate() && onNext()}
        >
          Next
        </button>
      </div>
    </div>
  );
}