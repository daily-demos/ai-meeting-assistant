import { AIAssistant } from "../components/AIAssistant";
import { useRouter } from "next/router";

export default () => {
  const { query } = useRouter();
  return <AIAssistant roomUrl={query?.room_url} />;
};
