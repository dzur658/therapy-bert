import { RouterProvider } from "react-router";
import { router } from "./routes";
import { PatientProvider } from "./context/patient-context";

export default function App() {
  return (
    <PatientProvider>
      <RouterProvider router={router} />
    </PatientProvider>
  );
}
