import { Routes, Route } from "react-router-dom";
import { Layout } from "./Layout";
import { Dashboard } from "./pages/Dashboard";
import { Sessions } from "./pages/Sessions";
import { ToolsHub } from "./pages/ToolsHub";
import { AppsHub } from "./pages/AppsHub";
import { Chat } from "./pages/Chat";
import { Help } from "./pages/Help";
import { Settings } from "./pages/Settings";
import { StatusAudit } from "./pages/StatusAudit";
import { ApiDocs } from "./pages/ApiDocs";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/tools" element={<ToolsHub />} />
        <Route path="/apps" element={<AppsHub />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/help" element={<Help />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/status" element={<StatusAudit />} />
        <Route path="/api-docs" element={<ApiDocs />} />
      </Routes>
    </Layout>
  );
}
