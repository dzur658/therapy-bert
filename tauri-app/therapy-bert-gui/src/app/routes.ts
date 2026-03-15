import { createBrowserRouter } from "react-router";
import { DashboardPage } from "./components/dashboard-page";
import { PatientDetailPage } from "./components/patient-detail-page";
import { KnowledgeGraphPage } from "./components/knowledge-graph-page";
import { SessionsPage } from "./components/sessions-page";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: DashboardPage,
  },
  {
    path: "/patient/:patientId",
    Component: PatientDetailPage,
  },
  {
    path: "/patient/:patientId/sessions",
    Component: SessionsPage,
  },
  {
    path: "/patient/:patientId/graph",
    Component: KnowledgeGraphPage,
  },
]);
