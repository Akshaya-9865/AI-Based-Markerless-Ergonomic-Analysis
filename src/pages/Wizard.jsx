import { useState } from "react";
import Stepper from "../components/Stepper";
import UploadStep from "../components/UploadStep";
import SubjectStep from "../components/SubjectStep";
import AnalyzeStep from "../components/AnalyzeStep";
import ResultsStep from "../components/ResultsStep";

export default function Wizard() {
  const [step, setStep] = useState(1);

  const [upload, setUpload] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [result, setResult] = useState(null);

  const [subject, setSubject] = useState({
    subject_name: "",
    age_years: 0,
    sex: "Male",
    height_cm: 0,
    weight_kg: 0,
    camera_distance_m: 1.0,
    recording_date: new Date().toISOString().slice(0, 10),
    seat_reference_length_cm: 50,
    seat_reference_pixel_length: 700,
  });

  function resetAll() {
    setStep(1);
    setUpload(null);
    setJobId(null);
    setResult(null);
    setSubject({
      subject_name: "",
      age_years: 0,
      sex: "Male",
      height_cm: 0,
      weight_kg: 0,
      camera_distance_m: 1.0,
      recording_date: new Date().toISOString().slice(0, 10),
      seat_reference_length_cm: 50,
      seat_reference_pixel_length: 700,
    });
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="glass p-6">
        <h1 className="text-2xl font-bold">Car Seating Comfort Motion Analysis</h1>
        <p className="text-white/70">Markerless kinematics • Comfort metrics • Research report exports</p>
      </div>

      <Stepper step={step} />

      {step === 1 && (
        <UploadStep
          onUploaded={(data) => setUpload(data)}
          onNext={() => setStep(2)}
        />
      )}

      {step === 2 && (
        <SubjectStep
          subject={subject}
          setSubject={setSubject}
          onBack={() => setStep(1)}
          onNext={() => setStep(3)}
        />
      )}

      {step === 3 && (
        <AnalyzeStep
          upload={upload}
          subject={subject}
          onJobStarted={(id) => setJobId(id)}
          jobId={jobId}
          onDone={(res) => {
            setResult(res);
            setStep(4);
          }}
          onBackToStart={resetAll}
        />
      )}

      {step === 4 && <ResultsStep result={result} onNew={resetAll} />}
    </div>
  );
}