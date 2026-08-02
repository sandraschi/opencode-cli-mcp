import { Routes, Route } from "react-router-dom";
import { Layout } from "./Layout";
import { Dashboard } from "./pages/Dashboard";
import { Sessions } from "./pages/Sessions";
import { Depot } from "./pages/Depot";
import { Backups } from "./pages/Backups";
import { Projects } from "./pages/Projects";
import { ToolsHub } from "./pages/ToolsHub";
import { AppsHub } from "./pages/AppsHub";
import { Chat } from "./pages/Chat";
import { Help } from "./pages/Help";
import { Settings } from "./pages/Settings";
import { StatusAudit } from "./pages/StatusAudit";
import { ApiDocs } from "./pages/ApiDocs";
import { McpbInstall } from "./pages/McpbInstall";
import { McpServers } from "./pages/McpServers";
import { Plugins } from "./pages/Plugins";
import { OpenCodeTools } from "./pages/OpenCodeTools";
import Logging from "./pages/Logging";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/depot" element={<Depot />} />
        <Route path="/backups" element={<Backups />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/tools" element={<ToolsHub />} />
        <Route path="/oc-tools" element={<OpenCodeTools />} />
        <Route path="/apps" element={<AppsHub />} />
        <Route path="/mcpb" element={<McpbInstall />} />
        <Route path="/mcp-servers" element={<McpServers />} />
        <Route path="/plugins" element={<Plugins />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/help" element={<Help />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/status" element={<StatusAudit />} />
        <Route path="/api-docs" element={<ApiDocs />} />
        <Route path="/logs" element={<Logging />} />
      </Routes>
    </Layout>
  );
}
