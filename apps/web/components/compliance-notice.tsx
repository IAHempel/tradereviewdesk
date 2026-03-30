import { StatePanel } from "@/components/state-panels";

export function ComplianceNotice({
  title = "Workflow support only",
  message = "TradeReviewDesk helps you prepare, document, and review your own decisions. It does not provide investment advice, security recommendations, execution, or brokerage services.",
}: {
  title?: string;
  message?: string;
}) {
  return <StatePanel title={title} message={message} tone="warning" />;
}
