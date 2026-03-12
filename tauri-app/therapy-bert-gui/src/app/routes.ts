import { createBrowserRouter } from "react-router";
import { DashboardPage } from "./components/dashboard-page";
import { PatientDetailPage } from "./components/patient-detail-page";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: DashboardPage,
  },
  {
    path: "/patient/:patientId",
    Component: PatientDetailPage,
  },
]);
