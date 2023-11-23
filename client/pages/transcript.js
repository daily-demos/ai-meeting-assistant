import { useRouter } from "next/router";
import { Transcript } from "../components/Transcript";

export default () => {
  const { query } = useRouter();
  return <Transcript roomUrl={query?.room_url} />;
};
