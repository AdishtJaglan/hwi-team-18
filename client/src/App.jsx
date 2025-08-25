import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing";
import ChatApp from "./pages/Bot";

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/home" element={<Landing />}></Route>
        <Route path="/bot" element={<ChatApp />}></Route>
        <Route path="/*" element={<Landing />}></Route>
      </Routes>
    </Router>
  );
};

export default App;
