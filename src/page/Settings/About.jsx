import { useState, useRef, useEffect } from "react";
import JoditEditor from "jodit-react";
import { message } from "antd";
import { useSelector } from "react-redux";
import { Navigate } from "../../Navigate";

const About = () => {
  const editor = useRef(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const { token } = useSelector((state) => state.logInUser);

  useEffect(() => {
    fetchAbout();
  }, []);

  const fetchAbout = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/legal/api/docs/about`);
      const data = await res.json();
      if (res.ok) {
        setContent(data.content);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/legal/api/docs/about`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ content })
      });
      const data = await res.json();
      if (res.ok) {
        message.success("About Us updated successfully!");
      } else {
        message.error(data.detail || "Failed to update About Us");
      }
    } catch (err) {
      console.error(err);
      message.error("An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const config = {
    readonly: false,
    placeholder: "Start typings...",
    style: {
      height: 650,
    },
    buttons: [
      "image",
      "fontsize",
      "bold",
      "italic",
      "underline",
      "|",
      "font",
      "brush",
      "align",
    ],
  };

  return (
    <div className=" bg-white p-3 min-h-screen">
       <Navigate title="About Us" />

      <JoditEditor
        ref={editor}
        value={content}
        config={config}
        tabIndex={1}
        onBlur={(newContent) => setContent(newContent)}
      />

      <div className="mt-5 flex justify-center">
        <button 
          onClick={handleSave}
          disabled={loading}
          className="bg-[#8B4513] py-2 px-6 rounded text-white hover:bg-opacity-90 transition disabled:opacity-70"
        >
          {loading ? "Saving..." : "Save & change"}
        </button>
      </div>
    </div>
  );
};

export default About;